import json
import asyncio
import logging
import shutil
from typing import Dict
from datetime import datetime
from pathlib import Path

import aiohttp

from .config import settings
from .models import MODELS
from .chunker import preprocess_text, split_text_into_chunks
from .llm_client import simplify_chunk_with_retry, get_api_key

logger = logging.getLogger(__name__)

simplification_tasks: Dict[str, dict] = {}
task_semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_TASKS)
token_log_lock = asyncio.Lock()

UPLOAD_DIR = settings.UPLOAD_DIR
SAVE_DIR = settings.SAVE_DIR
TOKEN_LOG = Path("token_log.json")

for d in [UPLOAD_DIR, SAVE_DIR]:
    d.mkdir(exist_ok=True)


async def log_tokens_atomic(task_id: str, prompt_tokens: int, completion_tokens: int):
    async with token_log_lock:
        log = {}
        if TOKEN_LOG.exists():
            try:
                log = json.loads(TOKEN_LOG.read_text(encoding="utf-8"))
            except Exception:
                log = {}

        today = datetime.now().strftime("%Y-%m-%d")
        if today not in log:
            log[today] = {"prompt_tokens": 0, "completion_tokens": 0, "total": 0}

        log[today]["prompt_tokens"] += prompt_tokens
        log[today]["completion_tokens"] += completion_tokens
        log[today]["total"] += prompt_tokens + completion_tokens

        temp_file = TOKEN_LOG.with_suffix(".tmp")
        try:
            temp_file.write_text(json.dumps(log, indent=2), encoding="utf-8")
            shutil.move(str(temp_file), str(TOKEN_LOG))
        except Exception as e:
            logger.error(f"Failed to write token log: {e}")
            if temp_file.exists():
                temp_file.unlink()


async def cleanup_task(task_id: str):
    delay = settings.TASK_CLEANUP_DELAY
    await asyncio.sleep(delay)

    if task_id in simplification_tasks:
        del simplification_tasks[task_id]
        logger.info(f"[{task_id[:8]}] Task cleaned up from memory")

    upload_file = UPLOAD_DIR / f"{task_id}.txt"
    if upload_file.exists():
        try:
            upload_file.unlink()
            logger.info(f"[{task_id[:8]}] Upload file cleaned up")
        except Exception as e:
            logger.warning(f"[{task_id[:8]}] Failed to cleanup upload file: {e}")


async def process_file(
    file_path: Path,
    task_id: str,
    original_filename: str,
    model: str = "qwen35-9b",
    action: str = "simplify",
):
    async with task_semaphore:
        logger.info(f"[{task_id[:8]}] Starting processing: {original_filename}")

        try:
            try:
                text = file_path.read_text(encoding="utf-8", errors="ignore")
            except Exception as e:
                raise Exception(f"Nelze přečíst soubor: {e}")

            if len(text) == 0:
                raise Exception("Soubor je prázdný")

            original_len = len(text)
            text = preprocess_text(text)
            preprocessed_len = len(text)

            if original_len != preprocessed_len:
                logger.info(
                    f"[{task_id[:8]}] Preprocessed: {original_len} -> {preprocessed_len} chars ({(1 - preprocessed_len / original_len) * 100:.1f}% saved)"
                )

            model_config = MODELS.get(model)
            if model_config is None:
                logger.warning(f"Model '{model}' není dostupný, používám qwen35-9b")
                model_config = MODELS["qwen35-9b"]
            chunk_size = model_config["chunk_size"]
            chunk_overlap = model_config.get("chunk_overlap", 0)

            chunks = split_text_into_chunks(text, chunk_size, chunk_overlap)
            total = len(chunks)

            logger.info(
                f"[{task_id[:8]}] File split into {total} chunks (size={chunk_size}, overlap={chunk_overlap})"
            )

            if total > 500:
                logger.warning(f"[{task_id[:8]}] Large file: {total} chunks")

            simplification_tasks[task_id] = {
                "status": "running",
                "current": 0,
                "total": total,
                "percent": 0,
                "filename": original_filename,
                "model": model,
                "action": action,
                "started": datetime.now().isoformat(),
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
            }

            api_key = get_api_key()
            simplified = []

            async with aiohttp.ClientSession() as session:
                for i, chunk in enumerate(chunks):
                    simplification_tasks[task_id]["current"] = i + 1
                    simplification_tasks[task_id]["percent"] = int(
                        ((i + 1) / total) * 100
                    )
                    logger.info(f"[{task_id[:8]}] Processing chunk {i + 1}/{total}")

                    try:
                        result, pt, ct = await simplify_chunk_with_retry(
                            session, chunk, api_key, model, action
                        )
                        simplified.append(result)

                        simplification_tasks[task_id]["prompt_tokens"] += pt
                        simplification_tasks[task_id]["completion_tokens"] += ct
                        simplification_tasks[task_id]["total_tokens"] += pt + ct

                        await log_tokens_atomic(task_id, pt, ct)
                        logger.info(
                            f"[{task_id[:8]}] Chunk {i + 1}/{total} done ({pt}+{ct} tokens)"
                        )

                    except Exception as e:
                        logger.error(f"[{task_id[:8]}] Chunk {i + 1} failed: {e}")
                        simplified.append(f"[ERROR: {str(e)[:100]}]")

                    if i < len(chunks) - 1:
                        logger.info(
                            f"[{task_id[:8]}] Cooldown {settings.CHUNK_COOLDOWN}s před dalším chunkem..."
                        )
                        await asyncio.sleep(settings.CHUNK_COOLDOWN)

            final = "\n\n".join(simplified)
            stem = Path(original_filename).stem
            output_name = f"{stem}_B1_cloud.txt"

            output_path = SAVE_DIR / output_name
            counter = 1
            while output_path.exists():
                output_name = f"{stem}_B1_cloud_{counter}.txt"
                output_path = SAVE_DIR / output_name
                counter += 1

            output_path.write_text(final, encoding="utf-8")

            simplification_tasks[task_id].update(
                {
                    "status": "completed",
                    "completed": datetime.now().isoformat(),
                    "output_file": output_name,
                }
            )

            logger.info(
                f"[{task_id[:8]}] Completed: {output_name} ({simplification_tasks[task_id]['total_tokens']} tokens)"
            )

        except Exception as e:
            error_msg = str(e)
            simplification_tasks[task_id].update(
                {
                    "status": "error",
                    "error": error_msg,
                    "completed": datetime.now().isoformat(),
                }
            )
            logger.error(f"[{task_id[:8]}] Error: {error_msg}")

        finally:
            asyncio.create_task(cleanup_task(task_id))
