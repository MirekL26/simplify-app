import os
import uuid
import json
import logging
from datetime import datetime
from pathlib import Path

import aiohttp
from fastapi import FastAPI, UploadFile, File, BackgroundTasks, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .config import settings
from .models import MODELS
from .task_manager import (
    simplification_tasks,
    UPLOAD_DIR,
    SAVE_DIR,
    TOKEN_LOG,
    process_file,
    task_semaphore,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Cloud B1 Simplifier",
    version="2.0.0",
)

BASE_DIR = Path(__file__).parent.parent
static_dir = BASE_DIR / "static"
templates_dir = BASE_DIR / "src" / "templates"

static_dir.mkdir(exist_ok=True)

app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
templates = Jinja2Templates(directory=str(templates_dir))


@app.get("/api/models")
async def list_models():
    return {
        "models": {
            k: {"label": v["label"], "chunk_size": v["chunk_size"]}
            for k, v in MODELS.items()
        }
    }


@app.get("/health")
async def health_check():
    health_status = {"status": "ok", "models": {}}

    async with aiohttp.ClientSession() as session:
        for model_key, config in MODELS.items():
            try:
                async with session.get(
                    config["health_url"], timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 200:
                        health_status["models"][model_key] = "ok"
                    else:
                        health_status["models"][model_key] = f"error:{response.status}"
                        health_status["status"] = "degraded"
            except Exception as e:
                health_status["models"][model_key] = f"unreachable:{str(e)[:50]}"
                health_status["status"] = "degraded"

    return health_status


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(
        "index.html", {"request": request, "models": MODELS}
    )


@app.post("/api/simplify")
async def simplify_upload(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    model: str = "qwen35-9b",
    action: str = "simplify",
):
    if model not in MODELS:
        model = "qwen35-9b"

    if action not in ["simplify", "translate"]:
        action = "simplify"

    content = await file.read()
    if len(content) > settings.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"Soubor je příliš velký (max {settings.MAX_FILE_SIZE_MB} MB)",
        )

    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Soubor je prázdný")

    task_id = str(uuid.uuid4())
    file_path = UPLOAD_DIR / f"{task_id}.txt"
    file_path.write_bytes(content)

    background_tasks.add_task(
        process_file,
        file_path,
        task_id,
        file.filename or "uploaded_file.txt",
        model,
        action,
    )

    logger.info(f"[{task_id[:8]}] Task started: {file.filename} ({len(content)} bytes)")

    return {
        "task_id": task_id,
        "filename": file.filename,
        "model": model,
        "action": action,
        "status": "started",
        "chunks_estimated": len(content) // 4000 + 1,
    }


@app.get("/api/task/{task_id}")
async def get_task(task_id: str):
    if task_id not in simplification_tasks:
        return JSONResponse(
            status_code=404, content={"error": "Task nenalezen nebo byl smazán"}
        )
    return simplification_tasks[task_id]


@app.get("/api/files")
async def list_files():
    files = []
    try:
        for f in sorted(
            SAVE_DIR.glob("*_B1_cloud*.txt"),
            key=lambda x: x.stat().st_mtime,
            reverse=True,
        ):
            files.append(
                {
                    "name": f.name,
                    "size": f.stat().st_size,
                    "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
                }
            )
    except Exception as e:
        logger.error(f"Error listing files: {e}")

    return {"files": files}


@app.get("/api/download/{filename}")
async def download(filename: str):
    filename = os.path.basename(filename)
    path = SAVE_DIR / filename

    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="Soubor nenalezen")

    return FileResponse(path, filename=filename)


@app.delete("/api/files/{filename}")
async def delete_file(filename: str):
    filename = os.path.basename(filename)
    path = SAVE_DIR / filename

    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="Soubor nenalezen")

    try:
        path.unlink()
        return {"status": "deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chyba při mazání: {e}")


@app.get("/api/tokens")
async def token_stats():
    if TOKEN_LOG.exists():
        try:
            return json.loads(TOKEN_LOG.read_text(encoding="utf-8"))
        except Exception as e:
            logger.error(f"Error reading token log: {e}")
            return {}
    return {}


@app.get("/api/active-tasks")
async def active_tasks():
    running = sum(
        1 for t in simplification_tasks.values() if t.get("status") == "running"
    )
    return {
        "running": running,
        "max_concurrent": settings.MAX_CONCURRENT_TASKS,
        "available_slots": settings.MAX_CONCURRENT_TASKS - running,
        "total_in_memory": len(simplification_tasks),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=settings.SIMPLIFIER_HOST,
        port=settings.SIMPLIFIER_PORT,
        reload=False,
    )
