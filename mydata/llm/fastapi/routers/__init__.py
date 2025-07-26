import json
from pathlib import Path

CONFIG_FILE = Path("/mydata/llm/fastapi/chat_logs/global_config.json")

DEFAULT_CONFIG = {
    "model": "gemma-jp:latest",
    "speaker_id": "0",
    "style_id": "0"
}

def save_global_config(model: str, speaker_id: str, style_id: str):
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with CONFIG_FILE.open("w", encoding="utf-8") as f:
        json.dump({
            "model": model,
            "speaker_id": speaker_id,
            "style_id": style_id,
        }, f, ensure_ascii=False, indent=2)

def load_global_config():
    if CONFIG_FILE.exists():
        try:
            with CONFIG_FILE.open("r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    config = json.loads(content)
                    return {
                        "model": config.get("model", DEFAULT_CONFIG["model"]),
                        "speaker_id": config.get("speaker_id", DEFAULT_CONFIG["speaker_id"]),
                        "style_id": config.get("style_id", DEFAULT_CONFIG["style_id"]),
                    }
        except Exception as e:
            print(f"❌ global_config.json 読み込み失敗: {e}")

    return DEFAULT_CONFIG.copy()
