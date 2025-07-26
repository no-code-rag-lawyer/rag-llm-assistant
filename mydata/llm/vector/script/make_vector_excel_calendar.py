#!/usr/bin/env python3
import os
import json
from pathlib import Path
from tqdm import tqdm
from sentence_transformers import SentenceTransformer
from chromadb import PersistentClient
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
from uid_utils import write_jsonl_atomic_sync

# === パス設定 ===
ROOT = Path("/mydata/llm/vector")
LOG_ROOT = ROOT / "db/log"
CHUNK_DIR = ROOT / "db/chunk"

CHUNK_LOG = LOG_ROOT / "chunk_log.jsonl"
VECTOR_DB_DIR = "/app/db/chroma/excel_calendar"
VECTOR_UID_LOG = LOG_ROOT / "vector_uid_excel_calendar.jsonl"
CONFIG_PATH = ROOT / "vector_config_vector_excel_calendar.json"  # ✅ 追加

MODEL_NAME = "/mydata/llm/vector/models/legal-bge-m3"  # ✅ 修正
THREAD_WORKERS = max(1, os.cpu_count() - 1)  # ✅ 構造維持
BATCH_CHUNK_SIZE, CHROMA_BATCH_SIZE, TIMEOUT_SEC = 500, 500, 300

# === 初期化 ===
client = PersistentClient(path=VECTOR_DB_DIR)
collection = client.get_or_create_collection("vector_excel_calendar", metadata={"hnsw:space": "cosine"})
model = SentenceTransformer(MODEL_NAME)

# === ヘルパー ===
def load_chunk_log() -> list:
    if not CHUNK_LOG.exists():
        print(f"[INFO] チャンクログが存在しません: {CHUNK_LOG}")
        return []
    chunks = []
    with CHUNK_LOG.open("r", encoding="utf-8") as f:
        for line in f:
            try:
                e = json.loads(line)
                if e.get("type") in ("excel", "calendar"):
                    chunks.append(e)
            except json.JSONDecodeError:
                continue
    return chunks

def get_existing_uids_from_db() -> set:
    try:
        existing = set()
        results = collection.get(include=["metadatas"])
        for meta in results.get("metadatas", []):
            uid = meta.get("uid")
            if uid:
                existing.add(uid)
        return existing
    except Exception as e:
        print(f"[WARN] DB UID取得失敗: {e}")
        return set()

def collect_target_chunks(all_chunks: list, valid_uids: set) -> list:
    return [c for c in all_chunks if c["uid"] not in valid_uids]

def load_chunk_texts(target_chunks: list) -> list:
    enriched = []
    for c in target_chunks:
        uid, index, rel_path, ftype = c["uid"], c["index"], c["path"], c["type"]
        chunk_file = CHUNK_DIR / (rel_path + ".jsonl")
        if not chunk_file.exists():
            print(f"[WARN] チャンクファイル未発見: {chunk_file}")
            continue
        try:
            with chunk_file.open("r", encoding="utf-8") as f:
                for line in f:
                    entry = json.loads(line)
                    if entry.get("index") == index:
                        enriched.append({
                            "uid": uid,
                            "index": index,
                            "path": rel_path,
                            "type": ftype,
                            "text": entry.get("text", "")
                        })
                        break
        except Exception as e:
            print(f"[WARN] チャンクファイル読み込み失敗: {chunk_file} ({e})")
    return enriched

def save_vector_uid_log(chunks: list):
    data = [
        {"uid": c["uid"], "index": c["index"], "path": c["path"], "type": c["type"]}
        for c in chunks
    ]
    write_jsonl_atomic_sync(VECTOR_UID_LOG, data)
    print(f"[INFO] VectorUIDログ更新: {VECTOR_UID_LOG.name}（{len(data)} 件）")

def encode_batch(texts):
    return model.encode(texts, convert_to_numpy=True, normalize_embeddings=True).tolist()

def add_to_chroma(emb, meta, ids, docs):
    for i in range(0, len(ids), CHROMA_BATCH_SIZE):
        collection.add(
            embeddings=emb[i:i + CHROMA_BATCH_SIZE],
            metadatas=meta[i:i + CHROMA_BATCH_SIZE],
            ids=ids[i:i + CHROMA_BATCH_SIZE],
            documents=docs[i:i + CHROMA_BATCH_SIZE]
        )

def save_vector_config():
    """✅ コンフィグを自動生成"""
    config = {
        "persist_directory": VECTOR_DB_DIR,
        "collection_name": "vector_excel_calendar",
        "embedding_model": MODEL_NAME,
        "normalize_embeddings": True
    }
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    print(f"[INFO] VectorConfig更新: {CONFIG_PATH.name}")

# === メイン ===
def main():
    print("▶️ make_vector_excel_calendar 開始（構造維持＋コンフィグ生成追加）")

    all_chunks = load_chunk_log()
    if not all_chunks:
        print("✅ チャンクログが空のため、処理なし")
        save_vector_config()
        return

    existing_uids = get_existing_uids_from_db()
    print(f"[INFO] DB登録済UID数: {len(existing_uids)}")

    target_chunks_meta = collect_target_chunks(all_chunks, existing_uids)
    if not target_chunks_meta:
        print("✅ 新規登録対象なし")
        save_vector_config()
        return

    target_chunks = load_chunk_texts(target_chunks_meta)
    print(f"[INFO] 登録対象チャンク数: {len(target_chunks)} 件")

    for i in range(0, len(target_chunks), BATCH_CHUNK_SIZE):
        batch = target_chunks[i:i + BATCH_CHUNK_SIZE]
        texts = [c["text"] for c in batch]
        ids = [f"{c['uid']}-{c['index']}" for c in batch]
        metas = [
            {
                "uid": c["uid"],
                "index": c["index"],
                "path": c["path"],
                "file_name": Path(c["path"]).stem,
                "type": c["type"]
            }
            for c in batch
        ]

        emb = []
        with ThreadPoolExecutor(max_workers=THREAD_WORKERS) as ex:
            futures = [ex.submit(encode_batch, [t]) for t in texts]
            for f in tqdm(as_completed(futures), total=len(futures),
                          desc=f"ベクトル生成中({i // BATCH_CHUNK_SIZE + 1}バッチ目)"):
                try:
                    emb.extend(f.result(timeout=TIMEOUT_SEC))
                except TimeoutError:
                    print("⚠️ タイムアウト発生、スキップ")

        add_to_chroma(emb, metas, ids, texts)

    save_vector_uid_log(all_chunks)
    save_vector_config()
    print(f"✅ Vector登録完了: 新規登録 {len(target_chunks)} 件 / 総計 {len(all_chunks)} 件")

if __name__ == "__main__":
    main()





























































































