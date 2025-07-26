#!/usr/bin/env python3
import json
from pathlib import Path
from uid_utils import read_jsonl, write_jsonl_atomic_sync, remove_empty_dirs

# === パス設定 ===
ROOT = Path("/mydata/llm/vector")
CHUNK_DIR = ROOT / "db/chunk"
LOG_ROOT = ROOT / "db/log"

TEXT_LOG = LOG_ROOT / "text_log.jsonl"
DELETED_TEXT_CALENDAR_LOG = LOG_ROOT / "deleted_text_calendar.jsonl"
CHUNK_LOG = LOG_ROOT / "chunk_log.jsonl"

def load_valid_uids() -> set:
    """テキストログ＋削除カレンダーログから有効UIDを収集"""
    valid_uids = set()
    if TEXT_LOG.exists():
        for e in read_jsonl(TEXT_LOG):
            if "uid" in e:
                valid_uids.add(e["uid"])
    if DELETED_TEXT_CALENDAR_LOG.exists():
        for e in read_jsonl(DELETED_TEXT_CALENDAR_LOG):
            if "uid" in e:
                valid_uids.add(e["uid"])
    return valid_uids

def delete_unnecessary_chunks(valid_uids: set) -> int:
    """テキストログにないUIDのチャンクを物理削除"""
    removed_count = 0
    for chunk_file in CHUNK_DIR.rglob("*.jsonl"):
        try:
            with chunk_file.open("r", encoding="utf-8") as f:
                first_line = f.readline().strip()
                if not first_line:
                    continue
                entry = json.loads(first_line)
                uid = entry.get("uid")
                if uid not in valid_uids:
                    chunk_file.unlink()
                    removed_count += 1
        except Exception as e:
            print(f"[WARN] チャンクファイル確認失敗: {chunk_file} ({e})")
    return removed_count

def rebuild_chunk_log():
    """実チャンクから最新のchunk_log.jsonlを再生成"""
    entries = []
    for chunk_file in CHUNK_DIR.rglob("*.jsonl"):
        try:
            with chunk_file.open("r", encoding="utf-8") as f:
                first_line = json.loads(f.readline())
                entries.append({
                    "uid": first_line.get("uid"),
                    "index": first_line.get("index"),
                    "path": first_line.get("path"),
                    "type": first_line.get("type", "unknown")
                })
        except Exception as e:
            print(f"[WARN] チャンクログ構築失敗: {chunk_file} ({e})")
            continue

    write_jsonl_atomic_sync(CHUNK_LOG, entries)
    print(f"[INFO] チャンクログ更新: {CHUNK_LOG.name}（{len(entries)} 件・fsync済）")

def main():
    print("▶️ delete_chunk.py 開始（最終設計準拠・空フォルダー削除対応）")
    valid_uids = load_valid_uids()
    print(f"[INFO] 有効UID数: {len(valid_uids)}")

    removed = delete_unnecessary_chunks(valid_uids)
    print(f"[INFO] 不要チャンク削除数: {removed}")

    rebuild_chunk_log()

    if removed:
        remove_empty_dirs(CHUNK_DIR, exclude=("calendar",))  # ✅ calendar残す

    print("✅ delete_chunk.py 完了")

if __name__ == "__main__":
    main()








