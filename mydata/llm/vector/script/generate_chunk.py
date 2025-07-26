#!/usr/bin/env python3
import json
import subprocess
from pathlib import Path
from uid_utils import read_jsonl, write_jsonl_atomic_sync, rebuild_chunk_log_fast

# === パス設定 ===
ROOT = Path("/mydata/llm/vector")
SCRIPT_ROOT = ROOT / "script"
LOG_ROOT = ROOT / "db/log"
TMP_ROOT = Path("/tmp")
CHUNK_DIR = ROOT / "db/chunk"

TEXT_LOG = LOG_ROOT / "text_log.jsonl"
CHUNK_LOG = LOG_ROOT / "chunk_log.jsonl"

SCRIPT_MAP = {
    "word": SCRIPT_ROOT / "make_chunk_word.py",
    "pdf": SCRIPT_ROOT / "make_chunk_pdf.py",
    "excel": SCRIPT_ROOT / "make_chunk_excel.py",
    "calendar": SCRIPT_ROOT / "make_chunk_calendar.py",
}

EXT_MAP = {
    "word": [".doc", ".docx", ".rtf"],
    "pdf": [".pdf"],
    "excel": [".xls", ".xlsx"],
    "calendar": [".json"],
}

def classify_targets():
    text_entries = read_jsonl(TEXT_LOG) if TEXT_LOG.exists() else []
    chunk_entries = read_jsonl(CHUNK_LOG) if CHUNK_LOG.exists() else []

    text_uids = {e["uid"]: e for e in text_entries}
    chunk_uids = {e["uid"] for e in chunk_entries}
    need_process_uids = set(text_uids.keys()) - chunk_uids

    categorized = {key: [] for key in EXT_MAP}
    for uid in need_process_uids:
        entry = text_uids[uid]
        rel_path = entry["path"]
        original_ext = Path(rel_path).with_suffix("").suffix.lower()
        for key, exts in EXT_MAP.items():
            if original_ext in exts:
                categorized[key].append({
                    "uid": uid,
                    "rel_path": rel_path,
                    "type": entry["type"]
                })
    return categorized

def dump_targets(categorized):
    for key, entries in categorized.items():
        if not entries:
            continue
        out_path = TMP_ROOT / f"targets_chunk_{key}.jsonl"
        with out_path.open("w", encoding="utf-8") as f:
            for entry in entries:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        print(f"[INFO] {key} 用ターゲット出力: {out_path}（{len(entries)} 件）")

def invoke_script(script_path: Path):
    try:
        subprocess.run(["python3", str(script_path)], check=True)
        print(f"[INFO] 実行完了: {script_path.name}")
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] 実行失敗: {script_path.name}\n{e}")

def main():
    print("▶️ generate_chunk.py 開始")
    categorized = classify_targets()

    if not any(categorized.values()):
        print("[INFO] チャンク生成対象なし")
        rebuild_chunk_log_fast(CHUNK_DIR, CHUNK_LOG)
        print("✅ generate_chunk 完了")
        return

    dump_targets(categorized)
    for key, script_path in SCRIPT_MAP.items():
        if not categorized[key]:
            print(f"[SKIP] {key} 処理なし")
            continue
        if not script_path.exists():
            print(f"[WARN] スクリプト未発見: {script_path}")
            continue
        invoke_script(script_path)

    rebuild_chunk_log_fast(CHUNK_DIR, CHUNK_LOG)
    print("✅ generate_chunk 完了")

if __name__ == "__main__":
    main()










