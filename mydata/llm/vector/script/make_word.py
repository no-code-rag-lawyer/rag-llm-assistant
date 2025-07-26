#!/usr/bin/env python3
import os
import time
import json
import shutil
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from datetime import datetime
from PyPDF2 import PdfReader
from concurrent.futures import ProcessPoolExecutor, as_completed

from uid_utils import generate_uid, get_relative_path  # ✅ 最終設計対応

LOCKFILE = Path("/tmp/lock_soffice.lock")
TMP_DIR = Path("/tmp/libre_pdf_output")

TARGET_LOG = Path("/tmp/targets_text_word.jsonl")  # ✅ generate_text.py に合わせる
TEXT_ROOT = Path("/mydata/llm/vector/db/text")
NAS_ROOT = Path("/mydata/nas")  # 元ファイル取得用
BATCH_SIZE = 100

def acquire_lock():
    while LOCKFILE.exists():
        try:
            with LOCKFILE.open() as f:
                pid = int(f.read().strip())
            os.kill(pid, 0)
            print(f"[INFO] LibreOffice 使用中（PID={pid}）、待機中...")
        except (ValueError, ProcessLookupError):
            print("[WARN] ロックファイルはあるがプロセスなし。削除して再取得。")
            LOCKFILE.unlink()
            continue
        time.sleep(1)
    with LOCKFILE.open("w") as f:
        f.write(str(os.getpid()))

def release_lock():
    if LOCKFILE.exists():
        try:
            LOCKFILE.unlink()
        except Exception as e:
            print(f"[WARN] ロック解除失敗: {e}")

def convert_to_pdf(batch):
    TMP_DIR.mkdir(exist_ok=True)
    env = dict(os.environ, HOME="/tmp/libre_home")
    try:
        subprocess.run(
            ["soffice", "--headless", "--convert-to", "pdf", "--outdir", str(TMP_DIR)]
            + [str(f) for f in batch],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            timeout=90,
            env=env
        )
        return True
    except subprocess.TimeoutExpired:
        print(f"[ERROR] LibreOffice変換がタイムアウトしました（{len(batch)}件）")
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] LibreOffice変換に失敗: {e.stderr.decode(errors='ignore')}")
    return False

def extract_text_and_save(pdf_path: Path, original_file: Path):
    try:
        reader = PdfReader(str(pdf_path))
        text_lines = []
        for i, page in enumerate(reader.pages):
            page_text = page.extract_text() or ""
            text_lines.append(f"<<page:{i+1}>>")
            text_lines.append(page_text.strip())

        # ===== メタ情報（最終設計準拠） =====
        rel_path = original_file.relative_to(NAS_ROOT)
        out_path = TEXT_ROOT / rel_path.with_name(rel_path.name + ".txt")
        out_path.parent.mkdir(parents=True, exist_ok=True)

        uid = generate_uid(original_file)
        abs_path = out_path.resolve()
        rel_text_path = get_relative_path(out_path, TEXT_ROOT)
        ftype = "word"
        stat = original_file.stat()
        mtime_iso = datetime.fromtimestamp(stat.st_mtime).isoformat()
        size = stat.st_size

        # ===== 書き込み =====
        with out_path.open("w", encoding="utf-8") as f:
            f.write(f"[UID]: {uid}\n")
            f.write(f"[ABS_PATH]: {abs_path}\n")
            f.write(f"[REL_PATH]: {rel_text_path}\n")
            f.write(f"[TYPE]: {ftype}\n")
            f.write(f"[MTIME]: {mtime_iso}\n")
            f.write(f"[SIZE]: {size}\n")
            f.write("----------------------------------------\n")
            f.write("\n".join(text_lines))

        return f"[OK] {original_file.name}"
    except Exception as e:
        return f"[ERROR] {pdf_path.name}: {e}"

def main():
    if not TARGET_LOG.exists():
        print("[INFO] Wordターゲットが見つかりません。スキップします。")
        return

    with TARGET_LOG.open(encoding="utf-8") as f:
        targets = [NAS_ROOT / Path(json.loads(line)["rel_path"]) for line in f if line.strip()]

    if not targets:
        print("[INFO] 有効なターゲットなし")
        return

    for i in range(0, len(targets), BATCH_SIZE):
        batch = targets[i:i + BATCH_SIZE]
        print(f"[INFO] Wordバッチ変換開始（{i}件目～{i+len(batch)-1}件目）")

        acquire_lock()
        success = convert_to_pdf(batch)
        release_lock()

        if not success:
            continue

        tasks = []
        with ProcessPoolExecutor() as executor:
            for original_file in batch:
                pdf_path = TMP_DIR / original_file.with_suffix(".pdf").name
                if pdf_path.exists():
                    tasks.append(executor.submit(extract_text_and_save, pdf_path, original_file))
                else:
                    print(f"[WARN] PDF未出力: {original_file.name}")
            for f in as_completed(tasks):
                print(f.result())

        for original_file in batch:
            pdf_path = TMP_DIR / original_file.with_suffix(".pdf").name
            if pdf_path.exists():
                pdf_path.unlink()

    shutil.rmtree(TMP_DIR, ignore_errors=True)
    TARGET_LOG.unlink(missing_ok=True)

if __name__ == "__main__":
    main()































