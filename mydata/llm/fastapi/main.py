import logging

logging.basicConfig(level=logging.INFO)

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import os
import requests

# === アプリ初期化 ===
app = FastAPI()

# === CORS設定（開発用：本番は制限すべき） ===
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === 静的ファイル（/static/index.html） ===
app.mount("/static", StaticFiles(directory="static"), name="static")

# === ルーター読み込み ===
from routers.chat import router as chat_router
from routers.chat_room import router as chat_room_router
from routers.config import router as config_router
from routers.voice import router as voice_router
from routers.vector_search import router as vector_router
from routers.model import router as model_router
from routers.voice_transcribe import router as voice_transcribe_router

# === ルーター登録（prefixは各routerで定義済） ===
app.include_router(chat_router)
app.include_router(chat_room_router)
app.include_router(config_router)
app.include_router(voice_router)
app.include_router(vector_router)
app.include_router(model_router)
app.include_router(voice_transcribe_router)

# === トップページ（開発中は http://localhost:8000/ で表示） ===
@app.get("/", response_class=FileResponse)
def serve_index():
    return FileResponse("static/index.html")