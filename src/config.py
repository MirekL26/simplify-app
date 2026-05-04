import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


class Settings:
    def __init__(self):
        self.SIMPLIFIER_HOST = os.getenv("SIMPLIFIER_HOST", "0.0.0.0")
        self.SIMPLIFIER_PORT = int(os.getenv("SIMPLIFIER_PORT", "8890"))
        self.LLM_NEMOTRON_URL = os.getenv(
            "SIMPLIFIER_NEMOTRON_URL", "http://192.168.0.74:8081/v1/chat/completions"
        )
        self.LLM_QWEN_URL = os.getenv(
            "SIMPLIFIER_QWEN_URL", "http://192.168.0.74:8082/v1/chat/completions"
        )
        self.SIMPLIFIER_API_KEY = os.getenv("SIMPLIFIER_API_KEY", "")
        self.MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "50"))
        self.MAX_CONCURRENT_TASKS = int(os.getenv("MAX_CONCURRENT_TASKS", "3"))
        self.TASK_CLEANUP_DELAY = int(os.getenv("TASK_CLEANUP_DELAY", "300"))
        self.CHUNK_COOLDOWN = int(os.getenv("CHUNK_COOLDOWN", "30"))
        self.UPLOAD_DIR = Path(os.getenv("SIMPLIFIER_UPLOAD_DIR", "./uploads"))
        self.SAVE_DIR = Path(os.getenv("SIMPLIFIER_SAVE_DIR", "./saved"))

    @property
    def MAX_FILE_SIZE(self) -> int:
        return self.MAX_FILE_SIZE_MB * 1024 * 1024


settings = Settings()
