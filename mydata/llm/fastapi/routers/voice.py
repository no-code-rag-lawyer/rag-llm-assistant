from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from fastapi.responses import JSONResponse
import os
import requests
import io
from pydub import AudioSegment
import re

router = APIRouter(prefix="/v1/voice")

VOICEVOX_HOST = os.getenv("VOICEVOX_HOST", "http://voicevox:50021")

# === ユーティリティ ===
def get_json(endpoint: str):
    try:
        res = requests.get(f"{VOICEVOX_HOST}{endpoint}")
        res.raise_for_status()
        return res.json()
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"VOICEVOX接続エラー: {str(e)}")

def split_sentences(text: str):
    # 「。」や改行で分割（空文は除外）
    parts = re.split(r'[。！？]\s*|\n+', text)
    return [p.strip() for p in parts if p.strip()]

# === 話者一覧取得 ===
@router.get("/speakers")
def get_speakers():
    try:
        speakers = get_json("/speakers")
        return {"success": True, "data": speakers, "error": None}
    except HTTPException as e:
        raise e

# === 音声合成用リクエスト形式 ===
class SynthesisRequest(BaseModel):
    text: str
    speaker_uuid: str
    style_id: int

# === 文単位の音声合成 API（保存なし版）===
@router.post("/synthesize_multi")
def synthesize_multi(body: SynthesisRequest):
    try:
        speaker_param = body.style_id
        sentences = split_sentences(body.text)
        audio_blobs = []

        for sentence in sentences:
            if not sentence:
                continue

            # STEP1: audio_query
            query_res = requests.post(
                f"{VOICEVOX_HOST}/audio_query",
                params={"text": sentence, "speaker": speaker_param}
            )
            query_res.raise_for_status()

            # STEP2: synthesis（WAVバイナリ取得）
            synth_res = requests.post(
                f"{VOICEVOX_HOST}/synthesis",
                params={"speaker": speaker_param},
                json=query_res.json()
            )
            synth_res.raise_for_status()

            # STEP3: MP3変換（メモリ上のみ）
            wav_bytes = io.BytesIO(synth_res.content)
            audio = AudioSegment.from_file(wav_bytes, format="wav")
            mp3_bytes = io.BytesIO()
            audio.export(mp3_bytes, format="mp3")
            mp3_bytes.seek(0)

            # クライアント用：hex文字列で返す
            audio_blobs.append(mp3_bytes.read().hex())

        return JSONResponse(content={"success": True, "data": audio_blobs, "error": None})

    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"VOICEVOX接続エラー: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"音声合成処理失敗: {str(e)}")
