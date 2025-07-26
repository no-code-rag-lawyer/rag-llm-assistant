import sqlite3

db_path = "/app/db/chroma/pdf_word/chroma.sqlite3"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print(f"=== {db_path} のテーブル一覧 ===")
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
for t in tables:
    print(f"テーブル: {t[0]}")

if "embeddings" in [t[0] for t in tables]:
    cursor.execute("SELECT COUNT(*) FROM embeddings;")
    print(f"=== embeddings テーブルの件数: {cursor.fetchone()[0]} 件 ===")

conn.close()











