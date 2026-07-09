import faiss
import numpy as np


def build_index(embeddings: list) -> faiss.IndexFlatIP:
    vectors = np.array(embeddings, dtype="float32")
    dimension = vectors.shape[1]
    faiss.normalize_L2(vectors)
    index = faiss.IndexFlatIP(dimension)
    index.add(vectors)
    return index


def search(index, query_embedding: list, chunks: list, top_k: int = 3) -> list:
    query_vector = np.array([query_embedding], dtype="float32")
    faiss.normalize_L2(query_vector)
    distances, indices = index.search(query_vector, top_k)

    results = []
    for i, idx in enumerate(indices[0]):
        results.append({
            "chunk": chunks[idx],
            "distance": float(distances[0][i])
        })
    return results


if __name__ == "__main__":
    try:
        from backend.embeddings import get_embeddings
        from backend.chunker import chunk_text
        from backend.parser import get_full_text
    except ImportError:
        from embeddings import get_embeddings
        from chunker import chunk_text
        from parser import get_full_text

    PDF_PATH = "/home/prashanna/Documents/AI_Research_Assistant/uploaded_papers/attention_is_all_you_need.pdf"
    full_text = get_full_text(PDF_PATH)
    chunks = chunk_text(full_text)
    embeddings = get_embeddings(chunks)

    index = build_index(embeddings)
    print(f"Index size: {index.ntotal} vectors")

    query = "What is the transformer architecture?"
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer("all-MiniLM-L12-v2")
    query_embedding = model.encode([query])[0].tolist()

    results = search(index, query_embedding, chunks, top_k=3)
    for i, r in enumerate(results):
        print(f"\nResult {i + 1} (similarity: {r['distance']:.4f}):")
        print(f"{r['chunk'][:200]}")
