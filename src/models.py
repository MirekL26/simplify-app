MODELS = {
    "nemotron-omni-30b": {
        "chunk_size": 20_000,
        "chunk_overlap": 200,
        "max_concurrent_chunks": 1,
        "label": "Nemotron 3 Nano Omni 30B (Local)",
        "api_format": "openai",
        "url": "http://192.168.0.74:8081/v1/chat/completions",
        "health_url": "http://192.168.0.74:8081/v1/models",
        "model_id": "Nemotron-3-Nano-Omni-30B",
    },
    "qwen35-9b": {
        "chunk_size": 8_000,
        "chunk_overlap": 150,
        "max_concurrent_chunks": 1,
        "label": "Qwen 3.5 9B Unsloth (Local)",
        "api_format": "openai",
        "url": "http://192.168.0.74:8082/v1/chat/completions",
        "health_url": "http://192.168.0.74:8082/v1/models",
        "model_id": "Qwen3.5-9B-Unsloth-UD-Q4_K_XL",
    },
}
