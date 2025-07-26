#!/usr/bin/env python3
import json
from pathlib import Path
from tqdm import tqdm

from uid_utils import generate_chunk_index  # ✅ インデックス付番用

TEXT_ROOT = Path("/mydata/llm/vector/db/text")
CHUNK_DIR = Path("/mydata/llm/vector/db/chunk")
TARGETS_JSONL = Path("/tmp/targets_chunk_calendar.jsonl")

def process_file(txt_path: Path, uid: str, ftype: str):
    """
    カレンダーファイルをチャンク化（基本1ファイル=1チャンク）し、最終設計準拠形式で保存
    """
    rel_path = str(txt_path.relative_to(TEXT_ROOT))

    with open(txt_path, "r", encoding="utf-8") as f:
        text = f.read().strip()

    # カレンダーは1チャンク固定
    record = {
        "uid": uid,                           # ✅ テキストログ由来UID
        "index": generate_chunk_index(0),     # 常に0
        "path": rel_path,
        "type": ftype,                        # calendar
        "text": text
    }

    out_path = CHUNK_DIR / (rel_path + ".jsonl")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

    return 1  # 常に1チャンク

def main():
    if not TARGETS_JSONL.exists():
        print(f"[INFO] 処理対象なし: {TARGETS_JSONL}")
        return

    with TARGETS_JSONL.open("r", encoding="utf-8") as f:
        targets = [json.loads(line) for line in f if line.strip()]

    if not targets:
        print("[INFO] 有効なターゲットなし")
        return

    print(f"▶️ Calendarチャンク生成開始: {len(targets)} 件")
    total_chunks = 0
    for t in tqdm(targets):
        txt_path = TEXT_ROOT / t["rel_path"]
        if not txt_path.exists():
            print(f"[WARN] テキストファイル未発見: {txt_path}")
            continue
        total_chunks += process_file(txt_path, uid=t["uid"], ftype=t["type"])

    print(f"✅ Calendarチャンク作成完了: 合計 {total_chunks} チャンク")

if __name__ == "__main__":
    main()








































