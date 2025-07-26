import json
import uuid
from pathlib import Path

ROOMS_FILE = Path("/mydata/llm/fastapi/chat_logs/rooms.json")

def load_rooms():
    if ROOMS_FILE.exists():
        try:
            with open(ROOMS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            # 壊れてる場合でもとりあえず初期化
            return {"rooms": []}
        except Exception as e:
            print(f"❌ rooms.json の読み込み失敗: {e}")
            return {"rooms": []}
    return {"rooms": []}

def save_rooms(data):
    try:
        ROOMS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(ROOMS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"❌ rooms.json の保存失敗: {e}")

def generate_room_id():
    return str(uuid.uuid4())
