from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sentence_transformers import SentenceTransformer
from chromadb import PersistentClient
from chromadb.config import Settings
from pathlib import Path
import json
import time  # ✅ 追加

app = FastAPI()

MODEL_NAME = "/mydata/llm/vector/models/legal-bge-m3"
model = SentenceTransformer(MODEL_NAME)

VECTOR_CONFIG_PATHS = [
    Path("/mydata/llm/vector/vector_config_vector_pdf_word.json"),
    Path("/mydata/llm/vector/vector_config_vector_excel_calendar.json"),
]

JOINABLE_SOURCES = {"pdf", "word"}
EXCEL_SOURCES = {"excel", "calendar"}

BASE_CHUNK_PATH = Path("/mydata/llm/vector/db/chunk")


def load_vector_configs():
    configs = []
    for path in VECTOR_CONFIG_PATHS:
        if path.exists():
            with path.open("r", encoding="utf-8") as f:
                config = json.load(f)
                configs.append(config)
    return configs


@app.post("/embed_search")
async def embed_search(request: Request):
    # ✅ リクエストID（ms単位のタイムスタンプ）
    req_id = int(time.time() * 1000)
    print(f"[INFO] === embed_search呼び出し開始 [{req_id}] ===")

    body = await request.json()
    query = body.get("query", "")
    keywords = body.get("keywords", [])
    type_filter = body.get("type")

    if not query:
        return JSONResponse(content={"success": False, "data": [], "error": "Missing query"}, status_code=400)

    threshold = body.get("threshold", 0.65)
    top_k = body.get("top_k", 50)
    raw_hits = []

    formatted_query = query
    embedding = model.encode([formatted_query], convert_to_numpy=True, normalize_embeddings=True).tolist()

    for config in load_vector_configs():
        try:
            client = PersistentClient(
                path=config["persist_directory"],
                settings=Settings(allow_reset=True)
            )
            collection = client.get_collection(name=config["collection_name"])

            response = collection.query(
                query_embeddings=embedding,
                n_results=top_k,
                include=["distances", "metadatas", "documents"]
            )
            print(f"[INFO] ▶ コレクション検索: {config.get('collection_name')}")

            for i in range(len(response["ids"][0])):
                distance = response["distances"][0][i]
                score = 1 - distance

                text = response["documents"][0][i]
                metadata = response["metadatas"][0][i]

                source = metadata.get("source") or metadata.get("type", "")
                chunk_type = metadata.get("type")

                if score >= threshold:
                    relative_path = metadata.get("path") or ""
                    absolute_path = str(BASE_CHUNK_PATH / relative_path)

                    raw_hits.append({
                        "score": score,
                        "uid": metadata.get("uid"),
                        "path": relative_path,
                        "absolute_path": absolute_path,
                        "chunk_index": metadata.get("chunk_index", -1),
                        "source": source,
                        "type": chunk_type,
                        "text": text.strip()
                    })
        except Exception as e:
            print(f"[ERROR] コレクション検索失敗: {config.get('collection_name')} → {e}")
            continue

    if type_filter:
        raw_hits = [c for c in raw_hits if c.get("source") in EXCEL_SOURCES and c.get("type") == type_filter]
        print(f"[INFO] ✅ type={type_filter} によるフィルタ適用後: {len(raw_hits)} 件")

    if keywords:
        for hit in raw_hits:
            kw_hits = sum(1 for kw in keywords if kw in hit["text"] or kw in hit["absolute_path"])
            if kw_hits > 0:
                hit["score"] += 0.1 * kw_hits
        print(f"[INFO] ✅ キーワード補正後スコア例: {[round(h['score'], 4) for h in raw_hits[:10]]}")

    context_hits = []
    added = set()
    raw_hits.sort(key=lambda x: x["score"], reverse=True)

    for main_hit in raw_hits[:3]:
        if main_hit["uid"] not in added:
            context_hits.append(main_hit)
            added.add(main_hit["uid"])

        if main_hit["source"] in JOINABLE_SOURCES:
            for adj_index in [main_hit["chunk_index"] - 1, main_hit["chunk_index"] + 1]:
                for candidate in raw_hits:
                    if (
                        candidate["source"] in JOINABLE_SOURCES
                        and candidate["path"] == main_hit["path"]
                        and candidate["chunk_index"] == adj_index
                        and candidate["uid"] not in added
                    ):
                        context_hits.append(candidate)
                        added.add(candidate["uid"])

    # ✅ 総合結果ログ
    if context_hits and context_hits[0]["source"] in JOINABLE_SOURCES:
        grouped = []
        last_chunk = None
        current_group = []
        for hit in context_hits:
            if last_chunk and last_chunk["path"] == hit["path"] and hit["chunk_index"] - last_chunk["chunk_index"] == 1:
                current_group.append(hit)
            else:
                if current_group:
                    grouped.append(current_group)
                current_group = [hit]
            last_chunk = hit
        if current_group:
            grouped.append(current_group)

        print(f"[INFO] 🔍 【総合結果】全チャンク数: {len(grouped)} 件")
        if grouped:
            flat = [h for g in grouped for h in g]
            print(f"[DEBUG] 【総合結果】スコア分布（上位50件）: {[round(h['score'], 4) for h in flat[:50]]}")

        return {"success": True, "data": grouped, "error": None}

    print(f"[INFO] 🔍 【総合結果】全チャンク数: {len(context_hits or raw_hits)} 件")
    if context_hits or raw_hits:
        print(f"[DEBUG] 【総合結果】スコア分布（上位50件）: {[round(h['score'], 4) for h in (context_hits or raw_hits)[:50]]}")

    return {"success": True, "data": context_hits or raw_hits, "error": None}



















