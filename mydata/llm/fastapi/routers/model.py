from fastapi import APIRouter
import os
import glob
import logging

router = APIRouter(prefix="/v1/model")

# === モデルディレクトリ（docker-composeのvolumeに合わせる）===
MODEL_DIR = os.getenv("MODEL_DIR", "/mydata/llm/llama/models")

@router.get("/list")
async def get_model_list():
    """
    /v1/model/list
    モデルディレクトリ以下をスキャンしてggufファイル一覧を返す
    """
    try:
        model_files = glob.glob(os.path.join(MODEL_DIR, "**/*.gguf"), recursive=True)
        models = []

        for model_file in model_files:
            relative_path = model_file.replace(MODEL_DIR, "")
            full_id = f"/models{relative_path}"

            models.append({
                "id": full_id,
                "name": os.path.splitext(os.path.basename(model_file))[0]  # ← 拡張子を除外
            })

        logging.info(f"[MODEL] スキャンモデル数: {len(models)} 件")
        return {"success": True, "data": models, "error": None}

    except Exception as e:
        logging.error(f"[MODEL] モデル一覧取得失敗: {e}")
        return {"success": False, "data": [], "error": str(e)}

