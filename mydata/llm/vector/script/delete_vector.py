#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
delete_vector.py（DB基準ログ対応・安定版）
- DBのメタデータ基準でゴーストファイル数 / チャンク数を正確にログ出力
- 削除対象はuid単位で安全に実行
"""

import json
from pathlib import Path
from chromadb import PersistentClient
from uid_utils import read_jsonl, write_jsonl_atomic_sync

# === 設定 ===
ROOT = Path("/mydata/llm/vector")
LOG_ROOT = ROOT / "db/log"

CHUNK_LOG = LOG_ROOT / "chunk_log.jsonl"

VECTOR_DB_DIRS = {
    "vector_pdf_word": "/app/db/chroma/pdf_word",
    "vector_excel_calendar": "/app/db/chroma/excel_calendar",
}

VECTOR_UID_LOGS = {
    "vector_pdf_word": LOG_ROOT / "vector_uid_pdf_word.jsonl",
    "vector_excel_calendar": LOG_ROOT / "vector_uid_excel_calendar.jsonl",
}

BATCH_SIZE = 500


def load_chunk_uids() -> set:
    """チャンクログからUIDを取得"""
    if not CHUNK_LOG.exists():
        print(f"[INFO] チャンクログが存在しません: {CHUNK_LOG}")
        return set()
    return {e.get("uid") for e in read_jsonl(CHUNK_LOG) if "uid" in e}


def get_db_ghost_file_map(db_path: str, collection_name: str, valid_uids: set) -> dict:
    """DBメタデータからゴーストファイルとチャンク数を集計"""
    ghost_file_map = {}
    client = PersistentClient(path=db_path)
    col = client.get_collection(collection_name)
    metas = col.get(include=["metadatas"]).get("metadatas", [])

    for m in metas:
        uid = m.get("uid")
        if not uid or uid in valid_uids:
            continue
        file_path = m.get("path")
        ghost_file_map.setdefault(file_path, []).append(uid)

    return ghost_file_map


def delete_from_chroma(db_path: str, collection_name: str, ghost_file_map: dict):
    """不要ベクトルをDBから削除（DBメタデータ基準のファイル/チャンク数ログ付）"""
    if not ghost_file_map:
        print(f"[INFO] {collection_name}: ゴーストなし")
        return

    total_files = len(ghost_file_map)
    total_chunks = sum(len(v) for v in ghost_file_map.values())

    print(f"🗑 {collection_name}: ゴースト検出 {total_files} ファイル / {total_chunks} チャンク（先頭10件表示）")
    for i, (file_path, uids) in enumerate(ghost_file_map.items()):
        if i >= 10:
            break
        print(f"  - {file_path}（{len(uids)} チャンク）")

    # UID単位で削除
    all_uids = [uid for uids in ghost_file_map.values() for uid in uids]
    client = PersistentClient(path=db_path)
    col = client.get_collection(collection_name)
    total_deleted = 0
    for i in range(0, len(all_uids), BATCH_SIZE):
        batch = all_uids[i:i + BATCH_SIZE]
        col.delete(where={"uid": {"$in": batch}})
        total_deleted += len(batch)
        print(f"[INFO] ベクトル削除: {collection_name}（{total_deleted}/{len(all_uids)} 件処理済）")

    print(f"[INFO] ベクトル削除完了: {collection_name}（合計 {total_files} ファイル / {total_chunks} チャンク）")


def save_vector_uid_log(path: Path, db_path: str, collection_name: str):
    """最新のDB状態からベクターログを再生成"""
    client = PersistentClient(path=db_path)
    if collection_name not in [c.name for c in client.list_collections()]:
        write_jsonl_atomic_sync(path, [])
        print(f"[INFO] VectorUIDログ空更新（コレクション未作成）: {path.name}")
        return

    col = client.get_collection(collection_name)
    metas = col.get(include=["metadatas"]).get("metadatas", [])
    data = [
        {
            "uid": m.get("uid"),
            "index": m.get("index"),
            "path": m.get("path"),
            "type": m.get("type"),
        }
        for m in metas if m.get("uid")
    ]
    write_jsonl_atomic_sync(path, data)
    print(f"[INFO] VectorUIDログ更新: {path.name}（{len(data)} 件）")


def main():
    print("▶️ delete_vector.py 開始（DB基準ログ対応・安定版）")

    valid_uids = load_chunk_uids()
    print(f"[INFO] 有効チャンクUID数: {len(valid_uids)}")

    for key, db_path in VECTOR_DB_DIRS.items():
        print(f"=== {key} 処理開始 ===")
        client = PersistentClient(path=db_path)
        collections = [c.name for c in client.list_collections()]
        if key not in collections:
            print(f"[INFO] {key}: 登録済みベクトルなし（スキップ）")
            save_vector_uid_log(VECTOR_UID_LOGS[key], db_path, key)
            continue

        ghost_file_map = get_db_ghost_file_map(db_path, key, valid_uids)
        delete_from_chroma(db_path, key, ghost_file_map)
        save_vector_uid_log(VECTOR_UID_LOGS[key], db_path, key)

    print("✅ delete_vector.py 完了")


if __name__ == "__main__":
    main()



























