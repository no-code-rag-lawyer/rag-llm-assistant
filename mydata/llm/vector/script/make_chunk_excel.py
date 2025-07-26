#!/usr/bin/env python3
import json
import re
from pathlib import Path
from tqdm import tqdm

from uid_utils import generate_chunk_index  # ✅ インデックス付番用

TEXT_ROOT = Path("/mydata/llm/vector/db/text")
CHUNK_DIR = Path("/mydata/llm/vector/db/chunk")
TARGETS_JSONL = Path("/tmp/targets_chunk_excel.jsonl")

SHEET_PATTERN = re.compile(r"<<sheet:(.*?)>>")

def classify_text(text: str) -> str:
    text = text.lower()
    if "電話" in text or "fax" in text or "〒" in text or "住所" in text \
        or any(x in text for x in ["tel", "fax"]) or (any(c in text for c in "0123456789") and "-" in text):
        return "contact"
    if any(w in text for w in ["連絡する", "提出予定", "依頼", "やること", "すること", "申請する"]):
        return "task"
    if any(w in text for w in ["連絡済", "提出した", "送った", "した", "完了", "済", "受領"]):
        return "done"
    if any(w in text for w in ["未了", "未済", "未提出", "控", "要対応", "未", "要送付"]):
        return "status"
    if any(w in text for w in ["費", "報酬", "給与", "振込", "入金", "出金", "支払", "経費", "利息"]):
        return "expense"
    return "memo"

def extract_keywords(text: str) -> str:
    keywords = []
    if re.search(r"\d{2,4}-\d{2,4}-\d{4}", text):
        keywords.append("電話番号")
    if re.search(r"\d{3}-\d{4}", text):
        keywords.append("郵便番号")
    if re.search(r"\d{4}[年/-]\d{1,2}[月/-]\d{1,2}", text):
        keywords.append("日付")
    if re.search(r"\d{1,3}(,\d{3})+円|\d+円", text):
        keywords.append("金額")
    if "FAX" in text.upper():
        keywords.append("FAX")
    if "住所" in text:
        keywords.append("住所")
    return "・".join(keywords)

def split_text_by_line(text):
    lines = text.splitlines()
    chunks = []
    current_sheet = ""
    for idx, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
        m = SHEET_PATTERN.match(line)
        if m:
            current_sheet = m.group(1)
            continue
        chunks.append((line, idx, current_sheet))
    return chunks

def process_file(txt_path: Path, uid: str, ftype: str):
    rel_path = str(txt_path.relative_to(TEXT_ROOT))

    with open(txt_path, "r", encoding="utf-8") as f:
        text = f.read()

    chunks = []
    for idx, (chunk_text, offset, sheet_name) in enumerate(split_text_by_line(text)):
        chunk_type = classify_text(chunk_text)
        keywords = extract_keywords(chunk_text)

        meta_text = f"[分類]: {chunk_type}\n[ファイル名]: /text/{rel_path}"
        if sheet_name:
            meta_text += f"\n[シート]: {sheet_name}"
        if keywords:
            meta_text += f"\n[キーワード候補]: {keywords}"

        record = {
            "uid": uid,                        # ✅ テキストログ由来UID
            "index": generate_chunk_index(idx),
            "path": rel_path,
            "type": ftype,                     # excel
            "text": f"{meta_text}\n{chunk_text}"
        }
        if sheet_name:
            record["sheet"] = sheet_name
        chunks.append(record)

    out_path = CHUNK_DIR / (rel_path + ".jsonl")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    return len(chunks)

def main():
    if not TARGETS_JSONL.exists():
        print(f"[INFO] 処理対象なし: {TARGETS_JSONL}")
        return

    with TARGETS_JSONL.open("r", encoding="utf-8") as f:
        targets = [json.loads(line) for line in f if line.strip()]

    if not targets:
        print("[INFO] 有効なターゲットなし")
        return

    print(f"▶️ Excelチャンク生成開始: {len(targets)} 件")
    total_chunks = 0
    for t in tqdm(targets):
        txt_path = TEXT_ROOT / t["rel_path"]
        if not txt_path.exists():
            print(f"[WARN] テキストファイル未発見: {txt_path}")
            continue
        total_chunks += process_file(txt_path, uid=t["uid"], ftype=t["type"])

    print(f"✅ Excelチャンク作成完了: 合計 {total_chunks} チャンク")

if __name__ == "__main__":
    main()












































