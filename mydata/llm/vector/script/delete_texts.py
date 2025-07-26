#!/usr/bin/env python3
import json
from pathlib import Path
from uid_utils import read_jsonl, write_jsonl_atomic_sync, remove_empty_dirs

# === パス設定 ===
ROOT = Path("/mydata/llm/vector")
TEXT_ROOT = ROOT / "db/text"
LOG_ROOT = ROOT / "db/log"

TEXT_LOG = LOG_ROOT / "text_log.jsonl"
DELETED_INPUT_LOG = LOG_ROOT / "deleted.jsonl"
DELETED_TEXT_LOG = LOG_ROOT / "deleted_texts.jsonl"
DELETED_TEXT_CALENDAR_LOG = LOG_ROOT / "deleted_text_calendar.jsonl"

def normalize_deleted_targets() -> set:
    """deleted.jsonlのパスをtext_log準拠に変換（.txt付与）"""
    targets = set()
    if not DELETED_INPUT_LOG.exists():
        return targets
    with DELETED_INPUT_LOG.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                data = json.loads(line)
                rel_path = data.get("rel_path")
                if rel_path:
                    targets.add(f"{rel_path}.txt")
            except json.JSONDecodeError:
                continue
    return targets

def remove_physical_texts(entries: list):
    """対応するテキストファイルを物理削除"""
    for entry in entries:
        text_file = TEXT_ROOT / entry["path"]
        try:
            if text_file.exists():
                text_file.unlink()
                print(f"[DEL] テキスト削除: {text_file}")
        except Exception as e:
            print(f"[WARN] テキスト削除失敗: {text_file} ({e})")

def main():
    print("▶️ delete_texts.py 開始（最終設計準拠・物理削除＋空フォルダー削除対応）")

    if not TEXT_LOG.exists():
        print(f"[INFO] テキストログが存在しません: {TEXT_LOG}")
        return

    deleted_targets = normalize_deleted_targets()
    if not deleted_targets:
        print("[INFO] 削除対象なし")
        return

    text_entries = read_jsonl(TEXT_LOG)
    remaining_entries, deleted_entries, deleted_calendar_entries = [], [], []

    for entry in text_entries:
        rel_path = entry.get("path")
        ftype = entry.get("type", "unknown")

        if rel_path in deleted_targets:
            if ftype == "calendar":
                deleted_calendar_entries.append(entry)
            else:
                deleted_entries.append(entry)
        else:
            remaining_entries.append(entry)

    # ✅ テキストログ更新
    write_jsonl_atomic_sync(TEXT_LOG, remaining_entries)
    print(f"[INFO] テキストログ更新: 残存 {len(remaining_entries)} 件")

    # ✅ 削除ログ更新
    if deleted_entries:
        write_jsonl_atomic_sync(DELETED_TEXT_LOG, deleted_entries)
        print(f"[INFO] 削除ログ更新: テキスト {len(deleted_entries)} 件")

    if deleted_calendar_entries:
        write_jsonl_atomic_sync(DELETED_TEXT_CALENDAR_LOG, deleted_calendar_entries)
        print(f"[INFO] 削除ログ更新: カレンダー {len(deleted_calendar_entries)} 件")

    # ✅ 物理削除＋空フォルダー掃除
    if deleted_entries or deleted_calendar_entries:
        remove_physical_texts(deleted_entries + deleted_calendar_entries)
        remove_empty_dirs(TEXT_ROOT, exclude=("calendar",))

    print("✅ delete_texts.py 完了")

if __name__ == "__main__":
    main()










