#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
uid_utils.py（最終決定版）
UID発番・インデックス付番・ログ操作・相対パス取得に特化
"""

import os
import json
import hashlib
import orjson
from pathlib import Path
from typing import List, Dict, Any

# ====== 1. UID生成（テキスト用・一元管理） ======
def generate_uid(file_path: Path) -> str:
    """
    UID = sha256(絶対パス + ファイル名 + タイムスタンプ + ファイルサイズ)
    ※本文は含めない
    ※ファイル移動・リネーム時には新UIDになる
    """
    stat = file_path.stat()
    uid_source = f"{file_path.resolve()}::{file_path.name}::{stat.st_mtime}::{stat.st_size}"
    return hashlib.sha256(uid_source.encode("utf-8")).hexdigest()

# ====== 2. チャンク用インデックス発番 ======
def generate_chunk_index(count: int) -> int:
    """
    チャンクのインデックス付番（0,1,2…）
    """
    return count

# ====== 3. JSONL操作 ======
def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    """JSONLファイルを読み込む（存在しない場合は空リストを返す）"""
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        return [json.loads(line.strip()) for line in f if line.strip()]

def write_jsonl_atomic_sync(path: Path, data: List[Dict[str, Any]]) -> None:
    """
    JSONLファイルをアトミック更新し、fsyncで書き込み保証
    ※全make系・delete系で標準利用
    """
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, path)
    print(f"[INFO] fsync付き書き込み完了: {path.name}（{len(data)} 件）")

# ====== 4. パス操作 ======
def get_relative_path(file_path: Path, base_path: Path) -> str:
    """
    基準パスからの相対パスを / 区切りで取得
    ログは相対パスで統一（可読性重視）
    """
    return str(file_path.relative_to(base_path)).replace("\\", "/")

# ====== 5. 汎用ヘルパー ======
def ensure_dir_exists(path: Path) -> None:
    """ディレクトリがなければ作成"""
    path.mkdir(parents=True, exist_ok=True)

# ====== 6. チャンクインデックス発番ログ ======
def rebuild_chunk_log_fast(chunk_dir: Path, log_path: Path) -> int:
    """
    チャンクフォルダ全体をスキャンして chunk_log.jsonl を再生成
    ✅ UID, index, path, type のみ高速収集（textは読み込まない）
    ✅ orjsonで高速パース
    """
    entries = []
    for chunk_file in chunk_dir.rglob("*.jsonl"):
        try:
            with chunk_file.open("r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    obj = orjson.loads(line)
                    entries.append({
                        "uid": obj["uid"],
                        "index": obj["index"],
                        "path": obj["path"],
                        "type": obj.get("type", "unknown")
                    })
        except Exception as e:
            print(f"[WARN] チャンクログ構築失敗: {chunk_file} ({e})")
            continue

    write_jsonl_atomic_sync(log_path, entries)
    print(f"[INFO] チャンクログ更新: {log_path.name}（{len(entries)} 件・fsync済）")
    return len(entries)
    
# ====== 7. 回帰的フォルダー抹消 ======
def remove_empty_dirs(base_dir: Path, exclude: tuple = ()):
    """
    base_dir配下の空フォルダーを再帰的に削除
    exclude: 削除しないフォルダー名（tupleで指定）
    """
    for dir_path in sorted(base_dir.rglob("*"), reverse=True):
        if dir_path.is_dir():
            # 除外フォルダー
            if dir_path.name in exclude:
                continue
            # 空フォルダーなら削除
            if not any(dir_path.iterdir()):
                try:
                    dir_path.rmdir()
                    print(f"[DEL] 空フォルダー削除: {dir_path}")
                except Exception as e:
                    print(f"[WARN] 空フォルダー削除失敗: {dir_path} ({e})")


