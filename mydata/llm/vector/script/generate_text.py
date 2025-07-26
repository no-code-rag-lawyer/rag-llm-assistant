#!/usr/bin/env python3
import json
import subprocess
from pathlib import Path
from uid_utils import (
    write_jsonl_atomic_sync,
    get_relative_path,
)

# === パス設定 ===
ROOT = Path("/mydata/llm/vector")
SCRIPT_ROOT = ROOT / "script"
LOG_ROOT = ROOT / "db/log"
TMP_ROOT = Path("/tmp")
TEXT_ROOT = ROOT / "db/text"

CHANGED_LOG = LOG_ROOT / "changed_files.jsonl"
TEXT_LOG = LOG_ROOT / "text_log.jsonl"

EXT_MAP = {
    "word": [".doc", ".docx", ".rtf"],
    "pdf": [".pdf"],
    "excel": [".xls", ".xlsx"],
    "calendar": [".json"],
}

SCRIPT_MAP = {
    "word": SCRIPT_ROOT / "make_word.py",
    "pdf": SCRIPT_ROOT / "make_pdf.py",
    "excel": SCRIPT_ROOT / "make_excel.py",
    "calendar": SCRIPT_ROOT / "make_calendar.py",
}

# === 1. 変更検出 ===
def classify_from_changed():
    if not CHANGED_LOG.exists():
        print(f"[INFO] changed_files.jsonl が存在しません: {CHANGED_LOG}")
        return {key: [] for key in EXT_MAP}

    categorized = {key: [] for key in EXT_MAP}
    with CHANGED_LOG.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue
            rel_path = data.get("rel_path")
            if not rel_path:
                continue
            ext = Path(rel_path).suffix.lower()
            for key, exts in EXT_MAP.items():
                if ext in exts:
                    categorized[key].append({"rel_path": rel_path})
    return categorized

def dump_targets(categorized):
    for key, entries in categorized.items():
        if not entries:
            continue
        out_path = TMP_ROOT / f"targets_text_{key}.jsonl"
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

# === 2. テキストログ再生成 ===
def extract_uid_from_text(text_path: Path) -> str:
    """
    テキストファイルからUIDを抽出する
    ※必ずUIDが埋め込まれている前提
    """
    with text_path.open("r", encoding="utf-8") as f:
        first_line = f.readline().strip()
        if not first_line.startswith("[UID]:"):
            raise ValueError(f"[ERROR] UID未埋め込み: {text_path}")
        return first_line.replace("[UID]:", "").strip()

def detect_type_from_ext(text_path: Path) -> str:
    """
    元ファイルの拡張子から種別判定
    例: "xxx.doc.txt" → ".doc" を取得
    """
    original_ext = Path(text_path.stem).suffix.lower()
    for key, exts in EXT_MAP.items():
        if original_ext in exts:
            return key
    return "unknown"

def rebuild_text_log():
    entries = []
    for path in TEXT_ROOT.rglob("*.txt"):
        uid = extract_uid_from_text(path)
        rel_path = get_relative_path(path, TEXT_ROOT)
        ftype = detect_type_from_ext(path)
        entries.append({"uid": uid, "path": rel_path, "type": ftype})
    write_jsonl_atomic_sync(TEXT_LOG, entries)
    print(f"[INFO] text_log更新: {TEXT_LOG}（{len(entries)} 件・fsync済）")

# === 3. メイン ===
def main():
    print("▶️ generate_text.py 開始")
    categorized = classify_from_changed()
    dump_targets(categorized)

    for key, script_path in SCRIPT_MAP.items():
        if not categorized.get(key):
            print(f"[SKIP] {key} 処理なし")
            continue
        if not script_path.exists():
            print(f"[WARN] スクリプト未発見: {script_path}")
            continue
        invoke_script(script_path)

    rebuild_text_log()
    print("✅ generate_text.py 完了")

if __name__ == "__main__":
    main()






















