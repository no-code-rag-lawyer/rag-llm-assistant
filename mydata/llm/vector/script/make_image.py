#!/usr/bin/env python3
import os
import re
import cv2
import pytesseract
import logging
import piexif
import json
from pathlib import Path
from datetime import datetime
from PIL import Image
from concurrent.futures import ProcessPoolExecutor, as_completed

from uid_utils import generate_uid, get_relative_path  # ✅ 最終設計対応

TEXT_ROOT = Path("/mydata/llm/vector/db/text")
NAS_ROOT = Path("/mydata/nas")
TARGETS_JSONL = Path("/tmp/targets_image.jsonl")

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

def clean_text(text: str) -> str:
    lines = text.splitlines()
    new_lines = []
    buffer = []

    for line in lines:
        stripped = line.strip()
        stripped = re.sub(r"(?<=\S)\s{1,}(?=\S)", "", stripped)

        if len(stripped) == 1:
            buffer.append(stripped)
        else:
            if len(buffer) >= 2:
                new_lines.append("".join(buffer))
                buffer.clear()
            elif buffer:
                new_lines.extend(buffer)
                buffer.clear()
            new_lines.append(stripped)

    if buffer:
        if len(buffer) >= 2:
            new_lines.append("".join(buffer))
        else:
            new_lines.extend(buffer)

    return "\n".join(new_lines)

def get_exif_datetime(img_path: Path) -> str:
    try:
        exif_dict = piexif.load(str(img_path))
        dt = exif_dict["Exif"].get(piexif.ExifIFD.DateTimeOriginal)
        if dt:
            return dt.decode("utf-8").replace(":", ".", 2).replace(":", ".")
    except Exception:
        pass
    return ""

def rotate_image(img, angle):
    (h, w) = img.shape[:2]
    M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
    return cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)

def preprocess_image_cv2(image_path: Path) -> list:
    img = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise ValueError(f"画像読み込み失敗: {image_path}")

    img = cv2.medianBlur(img, 3)  # ノイズ除去
    img = cv2.bitwise_not(img)
    thresh = cv2.adaptiveThreshold(img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                   cv2.THRESH_BINARY, 11, 2)
    img = cv2.bitwise_not(thresh)

    angles = [0, 90, 180, 270]
    rotated_images = [rotate_image(img, angle) for angle in angles]
    return rotated_images

def evaluate_text_quality(text: str) -> int:
    return len(re.findall(r"[\u4e00-\u9fafぁ-ん]", text))

def save_text(filepath: Path, text: str):
    # ===== メタ情報取得（最終設計準拠） =====
    rel_path = filepath.relative_to(NAS_ROOT)
    out_path = TEXT_ROOT / rel_path.with_suffix(".txt")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    uid = generate_uid(filepath)
    abs_path = out_path.resolve()
    rel_text_path = get_relative_path(out_path, TEXT_ROOT)
    ftype = "image"
    stat = filepath.stat()
    mtime_iso = datetime.fromtimestamp(stat.st_mtime).isoformat()
    size = stat.st_size
    exif_dt = get_exif_datetime(filepath)

    # ===== 書き込み =====
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(f"[UID]: {uid}\n")
        f.write(f"[ABS_PATH]: {abs_path}\n")
        f.write(f"[REL_PATH]: {rel_text_path}\n")
        f.write(f"[TYPE]: {ftype}\n")
        f.write(f"[MTIME]: {mtime_iso}\n")
        f.write(f"[SIZE]: {size}\n")
        if exif_dt:
            f.write(f"[EXIF_DATETIME]: {exif_dt}\n")
        f.write("----------------------------------------\n")
        f.write(text)

def process_image(path_str):
    path = Path(path_str)
    try:
        rotated_images = preprocess_image_cv2(path)
        best_score = 0
        best_text = ""

        for img in rotated_images:
            text = pytesseract.image_to_string(img, lang="jpn")
            score = evaluate_text_quality(text)
            if score > best_score:
                best_score = score
                best_text = text

        cleaned = clean_text(best_text)
        if len(cleaned.strip()) >= 10:
            save_text(path, cleaned)
            return f"[OK] {path}"
        else:
            return f"[WARN] 内容不足: {path}"

    except Exception as e:
        return f"[ERROR] {path}: {e}"

def main():
    if not TARGETS_JSONL.exists():
        logging.info(f"[INFO] 対象なし: {TARGETS_JSONL}")
        return

    paths = []
    with TARGETS_JSONL.open("r", encoding="utf-8") as f:
        for line in f:
            try:
                entry = json.loads(line)
                path = Path(entry["path"])
                if path.exists():
                    paths.append(str(path))
            except Exception as e:
                logging.warning(f"[WARN] JSON読み込み失敗: {e}")
                continue

    if not paths:
        logging.info("[INFO] 有効な画像ファイルがありません。")
        return

    logging.info(f"[INFO] 処理開始: {len(paths)} 件")

    with ProcessPoolExecutor() as executor:
        futures = [executor.submit(process_image, p) for p in paths]
        for f in as_completed(futures):
            print(f.result())

    logging.info("[DONE] 画像OCR完了")

if __name__ == "__main__":
    main()










