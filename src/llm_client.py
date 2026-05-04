import re
import asyncio
import logging
from pathlib import Path

import aiohttp

from .config import settings
from .models import MODELS

logger = logging.getLogger(__name__)


def get_api_key() -> str:
    if settings.SIMPLIFIER_API_KEY:
        return settings.SIMPLIFIER_API_KEY

    key_file = Path.home() / ".claude" / "ollama.md"
    if key_file.exists():
        try:
            return key_file.read_text().strip().splitlines()[0].strip()
        except Exception:
            pass
    return ""


def clean_output(text: str) -> str:
    text = re.sub(r"thinking.*?response", "", text, flags=re.DOTALL)
    match = re.search(r"<answer>(.*?)</answer>", text, re.DOTALL)
    if match:
        text = match.group(1)
    text = re.sub(
        r"^(Here is.*?:|Simplified.*?:|B1 version:|Translation.*?:)",
        "",
        text,
        flags=re.IGNORECASE | re.MULTILINE,
    )
    return text.strip()


async def simplify_chunk_with_retry(
    session: aiohttp.ClientSession,
    chunk: str,
    api_key: str,
    model_key: str,
    action: str,
    max_retries: int = 2,
) -> tuple[str, int, int]:
    if action == "translate":
        system_prompt = (
            "You are a professional translator and English editor. Your task is to translate the Czech text into English at B1 (intermediate) level. "
            "CRITICAL RULES: "
            "1. Translate the entire text accurately, keeping EVERY scene, sentence, and paragraph - do NOT summarize or skip anything. "
            "2. Use simple B1 level vocabulary and grammar, but keep the exact meaning. "
            "3. Keep the author's style, humor, and personality. "
            "Return ONLY the translated and simplified English text, without any explanations or introductory remarks."
        )
        user_prompt = f"Translate this Czech text into B1 level English:\n\n{chunk}"
    else:
        system_prompt = (
            "You are an expert English editor. Your task is to rewrite the text at B1 (intermediate) English level. "
            "CRITICAL RULES: "
            "1. Keep EVERY scene, sentence and paragraph - do NOT summarize or skip anything. "
            "2. Replace difficult words with simpler ones, but keep the same meaning and length. "
            "3. Keep the author's style, humor, and personality. "
            "4. The output should be similar in length to the input. "
            "Return ONLY the rewritten text, no explanations."
        )
        user_prompt = f"Simplify this text to B1 level:\n\n{chunk}"

    model_config = MODELS.get(model_key, MODELS["qwen35-9b"])
    api_format = model_config.get("api_format", "ollama")
    api_url = model_config.get("url")
    model_id = model_config.get("model_id")

    headers = {"Content-Type": "application/json"}
    if api_key and api_format == "ollama":
        headers["Authorization"] = f"Bearer {api_key}"

    payload = {
        "model": model_id,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
        "temperature": 0.7,
        "top_p": 0.95,
        "max_tokens": 8000,
        "cache_prompt": True,
    }

    last_error = None
    for attempt in range(max_retries + 1):
        try:
            async with session.post(
                api_url,
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=720),
            ) as response:
                if response.status == 200:
                    data = await response.json()

                    if api_format == "openai":
                        choices = data.get("choices", [])
                        content = (
                            choices[0].get("message", {}).get("content", chunk)
                            if choices
                            else chunk
                        )
                        usage = data.get("usage", {})
                        prompt_tokens = usage.get("prompt_tokens", 0)
                        completion_tokens = usage.get("completion_tokens", 0)
                    else:
                        content = data.get("message", {}).get("content", chunk)
                        prompt_tokens = data.get("prompt_eval_count", 0)
                        completion_tokens = data.get("eval_count", 0)

                    if prompt_tokens == 0 and completion_tokens == 0:
                        raise Exception(
                            "API nevrátilo tokeny - možná chyba rate limitu"
                        )

                    return clean_output(content), prompt_tokens, completion_tokens

                elif response.status == 429:
                    if attempt < max_retries:
                        wait = 2**attempt
                        logger.warning(f"Rate limit (429), retry in {wait}s...")
                        await asyncio.sleep(wait)
                        continue
                    raise Exception("Rate limit překročen (429) — počkej a zkus znovu")

                else:
                    error_text = await response.text()
                    raise Exception(f"API chyba {response.status}: {error_text[:200]}")

        except asyncio.TimeoutError:
            last_error = "Timeout - API neodpovědělo včas (10 min)"
            logger.warning(f"[{model_key}] Timeout on attempt {attempt + 1}")
            if attempt < max_retries:
                await asyncio.sleep(2)
            continue

        except Exception as e:
            last_error = str(e)
            logger.error(f"[{model_key}] Error on attempt {attempt + 1}: {e}")
            if attempt < max_retries:
                await asyncio.sleep(1)
            continue

    raise Exception(f"Všechny pokusy selhaly: {last_error}")
