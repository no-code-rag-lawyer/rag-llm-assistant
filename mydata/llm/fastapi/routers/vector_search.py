from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
import httpx
import logging

router = APIRouter(prefix="/v1/vector")

VECTOR_API_URL = os.getenv("VECTOR_API_URL", "http://vector:8000/embed_search")

class EmbedQuery(BaseModel):
    query: str

@router.post("/embed_search")
async def embed_search(req: EmbedQuery):
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="query is empty")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                VECTOR_API_URL,
                json={
                    "query": req.query,
                    "top_k": 100,
                    "threshold": 0.00
                }
            )
            response.raise_for_status()
            result = response.json()

            # ✅ data優先、なければchunks
            chunks = result.get("data", [])
            if not chunks:
                chunks = result.get("chunks", [])

            scores = []
            for group in chunks[:10]:
                if isinstance(group, list):
                    scores.extend([c.get("score", 0) for c in group])
                else:
                    scores.append(group.get("score", 0))
            logging.info(f"ベクトル検索レスポンス: 件数={len(chunks)}, 上位スコア={[round(s,4) for s in scores]}")

            return {
                "success": True,
                "data": chunks,
                "error": None
            }

    except httpx.RequestError as e:
        logging.error(f"❌ ベクトル検索通信失敗: {e}")
        raise HTTPException(status_code=500, detail=f"ベクトル検索通信失敗: {str(e)}")
    except httpx.HTTPStatusError as e:
        logging.error(f"❌ ベクトル検索HTTPエラー: {e.response.text}")
        raise HTTPException(status_code=e.response.status_code, detail=f"ベクトル検索失敗: {e.response.text}")
    except Exception as e:
        logging.error(f"❌ ベクトル検索例外: {e}")
        raise HTTPException(status_code=500, detail=f"不明なエラー: {str(e)}")






