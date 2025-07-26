#!/usr/bin/env python3
import subprocess
import os
import sys
from pathlib import Path

LOCK_FILE = Path("/tmp/run_all_pipeline.lock")

STEPS = [
    ("detect_changes",   "python3 /mydata/llm/vector/script/detect_changes.py"),
    ("delete_texts",     "python3 /mydata/llm/vector/script/delete_texts.py"),
    ("delete_chunk",     "python3 /mydata/llm/vector/script/delete_chunk.py"),
    ("delete_vector",    "python3 /mydata/llm/vector/script/delete_vector.py"),

    ("generate_text",    "python3 /mydata/llm/vector/script/generate_text.py"),
    ("generate_chunk",   "python3 /mydata/llm/vector/script/generate_chunk.py"),

    ("vector_pdf_word",  "python3 /mydata/llm/vector/script/make_vector_pdf_word.py"),
    ("vector_excel_cal", "python3 /mydata/llm/vector/script/make_vector_excel_calendar.py"),
  
    ("update_snapshot",  "python3 /mydata/llm/vector/script/update_snapshot.py"),
]

def main():
    if LOCK_FILE.exists():
        print("⚠️ 処理中の別インスタンスが存在します。終了します。")
        sys.exit(1)

    try:
        LOCK_FILE.write_text("locked")
        for name, command in STEPS:
            print(f"\n=== ▶ {name} ===")
            result = subprocess.run(command, shell=True)
            if result.returncode != 0:
                print(f"❌ {name} 失敗: {command}")
                break
            print(f"✅ {name} 完了")
    finally:
        if LOCK_FILE.exists():
            LOCK_FILE.unlink()

if __name__ == "__main__":
    main()
