#!/usr/bin/env python3
import os
import re
import fitz  # PyMuPDF
import json
import shutil
import logging
import subprocess
from pathlib import Path
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed

from uid_utils import generate_uid, get_relative_path  # ✅ 最終設計対応

TEXT_ROOT = Path("/mydata/llm/vector/db/text")
NAS_ROOT = Path("/mydata/nas")
TARGETS_JSONL = Path("/tmp/targets_text_pdf.jsonl")
TMP_ROOT = Path("/tmp/pdfocr")

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

def clean_text(text: str) -> str:
    text = re.sub(r"[\t\f\r]+", " ", text)
    text = re.sub(r"(?<=\S) +(?=\S)", "", text)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r'(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])', '', text)
    return text.strip()

def extract_text_and_pages(pdf_path: Path) -> tuple[str, int]:
    try:
        with fitz.open(pdf_path) as doc:
            text = "\n".join([page.get_text() for page in doc])
            return text, len(doc)
    except Exception as e:
        logging.error(f"[ERROR] PDF読み取り失敗: {pdf_path}: {e}")
        return "", 0

def save_text(filepath: Path, text: str, num_pages: int):
    # ===== メタ情報取得（最終設計準拠） =====
    rel_path = filepath.relative_to(NAS_ROOT)
    out_path = TEXT_ROOT / rel_path.with_name(rel_path.name + ".txt")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    uid = generate_uid(filepath)
    abs_path = out_path.resolve()
    rel_text_path = get_relative_path(out_path, TEXT_ROOT)
    ftype = "pdf"
    stat = filepath.stat()
    mtime_iso = datetime.fromtimestamp(stat.st_mtime).isoformat()
    size = stat.st_size

    # ===== 書き込み =====
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(f"[UID]: {uid}\n")
        f.write(f"[ABS_PATH]: {abs_path}\n")
        f.write(f"[REL_PATH]: {rel_text_path}\n")
        f.write(f"[TYPE]: {ftype}\n")
        f.write(f"[MTIME]: {mtime_iso}\n")
        f.write(f"[SIZE]: {size}\n")
        f.write(f"[PAGES]: {num_pages}\n")
        f.write("----------------------------------------\n")
        f.write(text)

def perform_ocr(pdf_path: Path) -> bool:
    TMP_ROOT.mkdir(parents=True, exist_ok=True)
    tmp_out = TMP_ROOT / (pdf_path.name + ".ocr.pdf")

    try:
        subprocess.run([
            "ocrmypdf", str(pdf_path), str(tmp_out),
            "--rotate-pages", "--deskew", "--language", "jpn",
            "--output-type", "pdf", "--force-ocr"
        ], check=True)
    except Exception as e:
        logging.error(f"[ERROR] OCR失敗: {pdf_path}: {e}")
        return False

    try:
        original_mtime = pdf_path.stat().st_mtime
        backup = pdf_path.with_suffix(".BK")
        pdf_path.rename(backup)
        try:
            shutil.copy(str(tmp_out), str(pdf_path))
            os.utime(pdf_path, (original_mtime, original_mtime))
            backup.unlink()
            return True
        except Exception as e:
            logging.error(f"[ERROR] OCR結果の置換失敗: {pdf_path} ← {tmp_out}: {e}")
            backup.rename(pdf_path)
            return False
    finally:
        if tmp_out.exists():
            tmp_out.unlink()

def process_pdf(filepath: Path):
    text, num_pages = extract_text_and_pages(filepath)
    cleaned = clean_text(text)

    if len(cleaned) >= 50:
        save_text(filepath, cleaned, num_pages)
        return f"[OK] {filepath}"
    else:
        logging.info(f"[INFO] OCR再試行: {filepath}")
        if perform_ocr(filepath):
            text, num_pages = extract_text_and_pages(filepath)
            cleaned = clean_text(text)
            if len(cleaned) >= 50:
                save_text(filepath, cleaned, num_pages)
                return f"[OK] {filepath}"
        return f"[WARN] 内容不足: {filepath}"

def main():
    if not TARGETS_JSONL.exists():
        logging.info(f"[INFO] PDF対象なし: {TARGETS_JSONL}")
        return

    paths = []
    with TARGETS_JSONL.open("r", encoding="utf-8") as f:
        for line in f:
            try:
                entry = json.loads(line)
                filepath = NAS_ROOT / Path(entry["rel_path"])
                if filepath.exists() and filepath.suffix.lower() == ".pdf":
                    paths.append(filepath)
            except Exception as e:
                logging.warning(f"[WARN] JSON読み込み失敗: {e}")
                continue

    if not paths:
        logging.info("[INFO] 有効なPDFファイルがありません。")
        return

    logging.info(f"[INFO] PDF処理開始: {len(paths)} 件")

    with ProcessPoolExecutor() as executor:
        futures = [executor.submit(process_pdf, p) for p in paths]
        for f in as_completed(futures):
            print(f.result())

    logging.info("[DONE] PDF処理完了")

if __name__ == "__main__":
    main()
























