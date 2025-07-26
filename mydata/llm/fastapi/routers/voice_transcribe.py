import os
import logging
from faster_whisper import WhisperModel
from fastapi import APIRouter, File, UploadFile

# ✅ Hugging Faceのキャッシュ先を変更（書き込み可能な /tmp を指定）
os.environ["HF_HOME"] = "/tmp/huggingface"

router = APIRouter(prefix="/v1/audio")

# ✅ Whisperモデル初期化
#   - "base"は精度と速度のバランスが良い
#   - CPU運用なら compute_type="int8" が推奨（軽量）
model_name = os.getenv("WHISPER_MODEL", "base")
model = WhisperModel(model_name, device="cpu", compute_type="int8")

@router.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    """
    アップロードされた音声ファイルを文字起こしする
    """
    try:
        # 一時保存
        audio_path = f"/tmp/{file.filename}"
        with open(audio_path, "wb") as f:
            f.write(await file.read())

        logging.info(f"[FASTER-WHISPER] 音声認識開始: {file.filename} (model={model_name})")
        segments, info = model.transcribe(audio_path, beam_size=5, language="ja")
        text = " ".join([segment.text for segment in segments])

        # 一時ファイル削除
        os.remove(audio_path)

        return {
            "success": True,
            "text": text,
            "language": info.language,
            "duration": info.duration
        }

    except Exception as e:
        logging.error(f"[WHISPER ERROR]: {e}")
        return {"success": False, "error": str(e)}



