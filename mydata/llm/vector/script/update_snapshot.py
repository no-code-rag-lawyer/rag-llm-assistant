#!/usr/bin/env python3
import json
from pathlib import Path
from uid_utils import write_jsonl_atomic_sync

# === パス設定 ===
ROOT = Path("/mydata/llm/vector")
NAS_ROOT = Path("/mydata/nas")
LOG_ROOT = ROOT / "db/log"

SNAPSHOT_LOG = LOG_ROOT / "snapshot.jsonl"

# === 除外パターン ===
EXCLUDE_KEYWORDS = (
    ".DS_Store",  # macOSメタ情報
    "._",         # Appleダブルファイル
    "_DAV",       # DAVキャッシュ
    "@eaDir",     # Synologyサムネイルフォルダー
    "$RECYCLE.BIN",  # Windowsゴミ箱
    ".Trash",        # macOSゴミ箱
    ".Recycle",      # QNAP等のゴミ箱
    "Thumbs.db"      # Windowsサムネイルキャッシュ
)

def is_excluded(path: Path) -> bool:
    """
    ゴミファイル・隠しファイル・隠しフォルダーを除外
    """
    for part in path.parts:
        if part.startswith("."):  # 隠しファイル/フォルダー（Unix系）
            return True
        if any(keyword in part for keyword in EXCLUDE_KEYWORDS):
            return True
    return False

def build_snapshot():
    """
    NAS全体をスキャンしてスナップショットを構築
    ✅ rel_path, mtime, size のみ（高速化版）
    ✅ ゴミファイル/隠しファイルを除外
    """
    entries = []
    for file in NAS_ROOT.rglob("*"):
        if not file.is_file():
            continue
        if is_excluded(file):
            continue
        try:
            stat = file.stat()
            entries.append({
                "rel_path": file.relative_to(NAS_ROOT).as_posix(),
                "mtime": stat.st_mtime,
                "size": stat.st_size
            })
        except Exception as e:
            print(f"[WARN] スナップショット取得失敗: {file} ({e})")

    write_jsonl_atomic_sync(SNAPSHOT_LOG, entries)
    print(f"[INFO] fsync付き書き込み完了: {SNAPSHOT_LOG.name}（{len(entries)} 件）")

def main():
    print("▶️ update_snapshot.py 開始（最終設計準拠・ゴミ/隠しファイル無視版）")
    build_snapshot()
    print("✅ update_snapshot.py 完了")

if __name__ == "__main__":
    main()















