#!/usr/bin/env python3
import json
from pathlib import Path
from uid_utils import read_jsonl, write_jsonl_atomic_sync

# === パス設定 ===
ROOT = Path("/mydata/llm/vector")
LOG_ROOT = ROOT / "db/log"

SNAPSHOT_LOG = LOG_ROOT / "snapshot.jsonl"
CHANGED_LOG = LOG_ROOT / "changed_files.jsonl"
DELETED_LOG = LOG_ROOT / "deleted.jsonl"

# === 除外パターン ===
EXCLUDE_KEYWORDS = (
    ".DS_Store", "._", "_DAV", "@eaDir", "$RECYCLE.BIN",
    ".Trash", ".Recycle", "Thumbs.db"
)

# === 対象拡張子 ===
VALID_EXTS = (".doc", ".docx", ".rtf", ".pdf", ".xls", ".xlsx", ".json")

def is_excluded(path: Path) -> bool:
    """ゴミファイル・隠しファイル・対象外ファイルを除外"""
    if any(part.startswith(".") for part in path.parts):
        return True
    if any(keyword in part for part in path.parts for keyword in EXCLUDE_KEYWORDS):
        return True
    if path.suffix.lower() not in VALID_EXTS:
        return True
    return False

def load_snapshot(path: Path) -> dict:
    """既存スナップショットを読み込む"""
    if not path.exists():
        return {}
    snapshot = {}
    for entry in read_jsonl(path):
        snapshot[entry["rel_path"]] = (entry["mtime"], entry["size"])
    return snapshot

def build_current_snapshot(nas_root: Path) -> dict:
    """現在のNAS状態を取得"""
    snapshot = {}
    for file in nas_root.rglob("*"):
        if not file.is_file():
            continue
        if is_excluded(file):
            continue
        try:
            stat = file.stat()
            snapshot[file.relative_to(nas_root).as_posix()] = (stat.st_mtime, stat.st_size)
        except Exception as e:
            print(f"[WARN] スナップショット取得失敗: {file} ({e})")
    return snapshot

def compare_snapshots(old: dict, new: dict):
    """スナップショット差分比較（更新は削除+新規扱い）"""
    changed, deleted = [], []
    for rel_path, (mtime, size) in new.items():
        if rel_path not in old:
            # ✅ 新規追加
            changed.append({"rel_path": rel_path, "mtime": mtime, "size": size})
        elif old[rel_path] != (mtime, size):
            # ✅ 更新扱い → 旧データは削除、新データは新規
            deleted.append({
                "rel_path": rel_path,
                "mtime": old[rel_path][0],
                "size": old[rel_path][1]
            })
            changed.append({"rel_path": rel_path, "mtime": mtime, "size": size})
    for rel_path in old:
        if rel_path not in new:
            deleted.append({
                "rel_path": rel_path,
                "mtime": old[rel_path][0],
                "size": old[rel_path][1]
            })
    return changed, deleted

# === メイン ===
def main():
    print("▶️ detect_changes.py 開始（スナップショット保存削除版・更新=削除扱い改修）")

    NAS_ROOT = Path("/mydata/nas")

    old_snapshot = load_snapshot(SNAPSHOT_LOG)
    current_snapshot = build_current_snapshot(NAS_ROOT)

    changed, deleted = compare_snapshots(old_snapshot, current_snapshot)

    write_jsonl_atomic_sync(CHANGED_LOG, changed)
    write_jsonl_atomic_sync(DELETED_LOG, deleted)

    # ❌ save_snapshot(current_snapshot, SNAPSHOT_LOG) は削除（既存仕様維持）

    print(f"[RESULT] ✅ 更新・新規: {len(changed)} 件, 🗑 削除: {len(deleted)} 件")
    print("✅ detect_changes.py 完了")

if __name__ == "__main__":
    main()





























