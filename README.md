# Cloud B1 Simplifier

Web application for simplifying English ebooks to B1 (intermediate) level using local LLMs running on llama.cpp.

## Features

- Upload `.txt` files and simplify English text to B1 level
- Translate from Czech to B1 English
- Smart text chunking with overlap for context preservation
- Multi-model support (configure your own LLM endpoints)
- Real-time progress tracking
- Token usage statistics
- File management (download, delete)
- Dark theme UI

## Requirements

- Python 3.11+
- A running llama.cpp server (or any OpenAI-compatible API) with a capable LLM

## Quick Start

```bash
# Clone
git clone https://github.com/MirekL26/simplify-app.git
cd simplify-app

# Setup
python3 -m venv venv
venv/bin/pip install -r requirements.txt   # Linux/macOS
# or: venv\Scripts\pip install -r requirements.txt  # Windows

# Configure
cp .env.example .env
# Edit .env with your LLM server URLs

# Run
./start.sh        # Linux/macOS
# or: start.bat   # Windows
# or: venv/bin/python -m src.main
```

Open http://localhost:8890 in your browser.

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `SIMPLIFIER_HOST` | `0.0.0.0` | Server bind address |
| `SIMPLIFIER_PORT` | `8890` | Server port |
| `SIMPLIFIER_NEMOTRON_URL` | `http://192.168.0.74:8081/v1/chat/completions` | LLM server URL (model 1) |
| `SIMPLIFIER_QWEN_URL` | `http://192.168.0.74:8082/v1/chat/completions` | LLM server URL (model 2) |
| `SIMPLIFIER_API_KEY` | (empty) | API key for LLM server |
| `MAX_FILE_SIZE_MB` | `50` | Max upload file size |
| `MAX_CONCURRENT_TASKS` | `3` | Max parallel processing tasks |
| `SIMPLIFIER_UPLOAD_DIR` | `./uploads` | Upload directory |
| `SIMPLIFIER_SAVE_DIR` | `./saved` | Output directory |

## LLM Backend

The app requires an OpenAI-compatible API endpoint (e.g., llama.cpp server). Configure model definitions in `src/models.py`.

Default models:
- **Nemotron 3 Nano Omni 30B** — chunk size 20k chars
- **Qwen 3.5 9B Unsloth** — chunk size 8k chars

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Web UI |
| `GET` | `/health` | Health check |
| `GET` | `/api/models` | List available models |
| `POST` | `/api/simplify` | Upload and start processing |
| `GET` | `/api/task/{id}` | Get task status |
| `GET` | `/api/files` | List completed files |
| `GET` | `/api/download/{name}` | Download a file |
| `DELETE` | `/api/files/{name}` | Delete a file |
| `GET` | `/api/tokens` | Token usage stats |
| `GET` | `/api/active-tasks` | Active task count |

## Development

```bash
venv/bin/pip install -r requirements.txt
venv/bin/python -m src.main
```

## License

MIT — see [LICENSE](LICENSE)
