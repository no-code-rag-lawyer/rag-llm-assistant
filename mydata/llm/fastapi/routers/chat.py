import os
from fastapi import APIRouter, HTTPException
import asyncio
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List
import json
import httpx
import logging
from pathlib import Path

from .chat_room import save_streamed_message

router = APIRouter(prefix="/v1/chat")
logging.basicConfig(level=logging.INFO)

LLM_HOST = os.getenv("LLM_HOST", "http://llama:8000")
VECTOR_API_URL = os.getenv("VECTOR_API_URL", "http://vector:8000/embed_search")

PROMPT_DIR = Path("/mydata/llm/fastapi/config/prompts")

class Message(BaseModel):
    role: str
    content: str
    model: str = ""
    speaker_uuid: str = ""
    style_id: int = 0
    room_id: str = ""

class CompletionRequest(BaseModel):
    model: str
    messages: List[Message]
    stream: bool = True
    speaker_uuid: str = ""
    style_id: int = 0
    room_id: str = ""
    prompt_id: str = "rag_default"

async def extract_keywords_llm(query: str, model_name: str) -> List[str]:
    try:
        logging.info(f"[INFO] キーワード抽出開始: {query} (model={model_name})")
        payload = {
            "model": model_name,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "以下の文章から重要な名詞を最大5個抽出してください。\n"
                        "1. 複合語は1語として扱う\n"
                        "2. 法律名や制度名も1語として扱う\n"
                        "3. 一般的すぎる語（例: 事件, 裁判, 本件）は除外\n"
                        "出力は必ずJSON配列形式のみで返してください。"
                    )
                },
                {"role": "user", "content": query}
            ]
        }
        async with httpx.AsyncClient(timeout=20.0) as client:
            res = await client.post(f"{LLM_HOST}/v1/chat/completions", json=payload)
            res.raise_for_status()
            content = res.json()["choices"][0]["message"]["content"]
            keywords = json.loads(content)
            logging.info(f"[INFO] 抽出キーワード: {keywords}")
            return keywords if isinstance(keywords, list) else []
    except Exception as e:
        logging.warning(f"[WARN] キーワード抽出失敗: {e}")
        return []

async def vector_search_with_keywords(query: str, keywords: List[str], top_k: int = 50, threshold: float = 0.5, limit: int = 50):
    try:
        logging.info(f"ベクトル検索開始: {query} (keywords={keywords})")
        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.post(VECTOR_API_URL, json={
                "query": query,
                "keywords": keywords,
                "top_k": top_k,
                "threshold": threshold
            })
            res.raise_for_status()
            chunks = res.json().get("data", [])
            logging.info(f"[DEBUG] ベクトル検索件数: {len(chunks)}")
            return chunks[:limit] if isinstance(chunks, list) else []
    except Exception as e:
        logging.error(f"[vector_search error]: {e}")
        return []

def load_prompt_text(prompt_id: str, context_text: str = "") -> str:
    file_path = PROMPT_DIR / f"{prompt_id}.txt"
    if not file_path.exists():
        logging.warning(f"[PROMPT] {prompt_id}.txt が見つからないため rag_default を使用します")
        file_path = PROMPT_DIR / "rag_default.txt"
    lines = file_path.read_text(encoding="utf-8").splitlines()
    prompt_body = "\n".join(lines[1:]) if len(lines) > 1 else "\n".join(lines)
    return prompt_body.replace("{context_text}", context_text)

@router.post("/completions")
async def completions(req: CompletionRequest):
    user_message = next((m.content for m in reversed(req.messages) if m.role == "user"), None)
    if not user_message:
        raise HTTPException(status_code=400, detail="No user message found")

    # ✅ ユーザー入力は即時書き込み
    if req.room_id and user_message:
        save_streamed_message(req.room_id, role="user", content=user_message, model="")

    keywords = await extract_keywords_llm(user_message, req.model)
    retrieved_chunks = await vector_search_with_keywords(user_message, keywords, top_k=50, threshold=0.5)

    pdf_word_texts, excel_calendar_texts = [], []
    for c in retrieved_chunks:
        targets = c if isinstance(c, list) else [c]
        for sub in targets:
            if isinstance(sub, dict) and isinstance(sub.get("text"), str):
                src = sub.get("source") or sub.get("type", "")
                file_info = f"[ファイル]: {sub.get('absolute_path', sub.get('path', '不明'))}"
                if src in {"pdf", "word"}:
                    pdf_word_texts.append(f"{file_info}\n{sub['text'].strip()}")
                elif src in {"excel", "calendar"}:
                    excel_calendar_texts.append(f"{file_info}\n{sub['text'].strip()}")

    if pdf_word_texts or excel_calendar_texts:
        context_parts = []
        if pdf_word_texts:
            context_parts.append("[PDF/Wordの参考情報]\n" + "\n\n".join(pdf_word_texts))
        if excel_calendar_texts:
            context_parts.append("[Excel/カレンダーの参考情報]\n" + "\n\n".join(excel_calendar_texts))
        context_text = "\n\n".join(context_parts)
    else:
        context_text = (
            "関連情報が見つかりませんでした。\n"
            f"以下のテーマについて一般的な知見に基づき回答してください。\n"
            f"テーマ: {user_message}"
        )

    logging.info(f"[DEBUG] RAGプロンプト先頭500文字:\n{context_text[:500]}")

    system_prompt = load_prompt_text(req.prompt_id, context_text)
    prompt_messages = [
        {"role": "system", "content": system_prompt},
        *[{"role": m.role, "content": m.content} for m in req.messages if m.content.strip()]
    ]

    payload = {
        "model": req.model,
        "messages": prompt_messages,
        "stream": True
    }

    try:
        async with httpx.AsyncClient(timeout=None) as client:
            response = await client.post(f"{LLM_HOST}/v1/chat/completions", json=payload)
            if not response.is_success:
                raise HTTPException(status_code=response.status_code, detail=f"LLM error: {response.text}")

            async def iter_response():
                buffer = []
                try:
                    async for chunk in response.aiter_text():
                        try:
                            clean = chunk.replace("data: ", "").strip()
                            if clean and clean != "[DONE]":
                                data = json.loads(clean)
                                delta = data.get("choices", [{}])[0].get("delta", {})
                                text_piece = delta.get("content", "")
                                if text_piece:
                                    buffer.append(text_piece)
                            elif clean == "[DONE]":
                                # ✅ DONE受信時点で書き込み
                                full_text = "".join(buffer).strip()
                                if req.room_id and full_text:
                                    save_streamed_message(
                                        req.room_id, role="assistant", content=full_text, model=req.model
                                    )
                        except Exception:
                            pass

                        yield chunk
                        await asyncio.sleep(0)
                finally:
                    # ✅ DONEが来なかった場合も終了時に必ず書き込む
                    if req.room_id and buffer:
                        full_text = "".join(buffer).strip()
                        save_streamed_message(
                            req.room_id, role="assistant", content=full_text, model=req.model
                        )

            return StreamingResponse(
                iter_response(),
                media_type="text/event-stream",
                headers={"Transfer-Encoding": "chunked"}
            )
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"LLM error: {e.response.text}")
    except Exception as e:
        import traceback
        logging.error(f"[COMPLETIONS ERROR]: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@router.get("/prompt/list")
async def list_prompts():
    try:
        prompts = []
        for f in PROMPT_DIR.glob("*.txt"):
            lines = f.read_text(encoding="utf-8").splitlines()
            display_name = lines[0].strip() if lines else f.stem
            prompts.append({"id": f.stem, "name": display_name})
        return {"success": True, "data": prompts, "error": None}
    except Exception as e:
        return {"success": False, "data": [], "error": str(e)}



















