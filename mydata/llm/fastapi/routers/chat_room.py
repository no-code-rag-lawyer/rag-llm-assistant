from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pathlib import Path
import json
import logging
from datetime import datetime

from .room_store import load_rooms, save_rooms, generate_room_id

router = APIRouter(prefix="/v1/chat")

CHAT_LOGS_DIR = Path("/mydata/llm/fastapi/chat_logs")
CHAT_LOGS_DIR.mkdir(parents=True, exist_ok=True)

class CreateRoomRequest(BaseModel):
    name: str

class RenameRoomRequest(BaseModel):
    room_id: str
    new_name: str

class MessageEntry(BaseModel):
    room_id: str
    message: dict

@router.get("/rooms")
def list_rooms():
    return {"success": True, "data": load_rooms()["rooms"], "error": None}

@router.post("/rooms")
def create_room(payload: CreateRoomRequest):
    room_id = generate_room_id()
    log_path = CHAT_LOGS_DIR / f"{room_id}.jsonl"
    try:
        log_path.touch()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ログファイル作成失敗: {e}")

    data = load_rooms()
    data["rooms"].append({"id": room_id, "name": payload.name})
    save_rooms(data)
    return {"success": True, "data": {"room_id": room_id}, "error": None}

@router.put("/rooms/rename")
def rename_room(payload: RenameRoomRequest):
    data = load_rooms()
    for r in data["rooms"]:
        if r["id"] == payload.room_id:
            r["name"] = payload.new_name
            break
    else:
        raise HTTPException(status_code=404, detail="Room not found")
    save_rooms(data)
    return {"success": True, "data": None, "error": None}

@router.delete("/rooms/{room_id}")
def delete_room(room_id: str):
    data = load_rooms()
    data["rooms"] = [r for r in data["rooms"] if r["id"] != room_id]
    save_rooms(data)
    log_file = CHAT_LOGS_DIR / f"{room_id}.jsonl"
    if log_file.exists():
        log_file.unlink()
    return {"success": True, "data": {"room_id": room_id}, "error": None}

@router.post("/messages")
def store_message(payload: MessageEntry):
    log_file = CHAT_LOGS_DIR / f"{payload.room_id}.jsonl"
    if not log_file.exists():
        raise HTTPException(status_code=404, detail="ログファイルが存在しません")

    # ✅ 修正：assistantの場合はモデル名をそのまま保存
    role = payload.message.get("role", "user")
    content = payload.message.get("content", "")
    model = payload.message.get("model", "") if role == "assistant" else ""

    entry = {
        "role": role,
        "content": content,
        "model": model,
        "timestamp": datetime.now().isoformat()
    }

    try:
        with log_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"書き込み失敗: {e}")

    return {"success": True, "data": None, "error": None}

@router.get("/messages/{room_id}")
def load_messages(room_id: str):
    log_file = CHAT_LOGS_DIR / f"{room_id}.jsonl"
    if not log_file.exists():
        raise HTTPException(status_code=404, detail="ログファイルが存在しません")
    messages = []
    try:
        with log_file.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        msg = json.loads(line)
                        if isinstance(msg, dict):
                            messages.append(msg)
                    except json.JSONDecodeError:
                        continue
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"読み込み失敗: {e}")
    return {"success": True, "data": messages, "error": None}

def save_streamed_message(room_id: str, role: str, content: str, model: str = ""):
    if not room_id:
        logging.warning("[LOG] room_idが空のためスキップ")
        return

    log_file = CHAT_LOGS_DIR / f"{room_id}.jsonl"
    if not log_file.exists():
        log_file.touch()

    entry = {
        "role": role,
        "content": content,
        "model": model if role == "assistant" else "",
        "timestamp": datetime.now().isoformat()
    }

    try:
        with log_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        logging.info(f"[LOG] ストリーミング書き込み: {room_id}")
    except Exception as e:
        logging.error(f"[LOG SAVE ERROR]: {e}")













