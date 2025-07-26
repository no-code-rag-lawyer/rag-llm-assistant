from chromadb import PersistentClient
from sentence_transformers import SentenceTransformer
from pathlib import Path

# === 設定 ===
MODEL_PATH = "/mydata/llm/vector/models/legal-bge-m3"
VECTOR_CONFIGS = [
    {
        "name": "vector_pdf_word",
        "path": "/mydata/llm/vector/db/chroma/pdf_word"
    },
    {
        "name": "vector_excel_calendar",
        "path": "/mydata/llm/vector/db/chroma/excel_calendar"
    }
]

def search_vector(query: str, top_k: int = 20):
    model = SentenceTransformer(MODEL_PATH)
    embedding = model.encode([query], convert_to_numpy=True, normalize_embeddings=True).tolist()

    for cfg in VECTOR_CONFIGS:
        print(f"\n=== ▶ コレクション検索: {cfg['name']} ===")
        try:
            client = PersistentClient(path=cfg["path"])
            collection = client.get_collection(name=cfg["name"])

            results = collection.query(
                query_embeddings=embedding,
                n_results=top_k,
                include=["distances", "metadatas", "documents"]
            )

            hits = []
            for i in range(len(results["ids"][0])):
                # --- コサイン類似度に変換（距離:0=完全一致,1=無関係 → 類似度:1=完全一致,0=無関係）
                distance = results["distances"][0][i]
                score = 1 - distance

                meta = results["metadatas"][0][i]
                text = results["documents"][0][i]
                hits.append({
                    "score": score,
                    "uid": meta.get("uid"),
                    "path": meta.get("path"),
                    "chunk_index": meta.get("chunk_index"),
                    "preview": text[:100].replace("\n", "")
                })

            # スコア順に並べ替え（高いほど類似）
            hits.sort(key=lambda x: x["score"], reverse=True)
            for h in hits:
                print(f"[{h['score']:.4f}] {h['uid']} | {h['path']} | #{h['chunk_index']} | {h['preview']}")

            if not hits:
                print("ヒットなし")
        except Exception as e:
            print(f"[ERROR] {cfg['name']} → {e}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("使用方法: python3 debugvs.py '検索語句'")
    else:
        query = sys.argv[1]
        search_vector(query)

