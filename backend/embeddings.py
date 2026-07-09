from sentence_transformers import SentenceTransformer

model = SentenceTransformer('all-MiniLM-L12-v2')

def get_embeddings(chunks: list) -> list:
    embeddings = model.encode(chunks, show_progress_bar=True)
    return embeddings.tolist()

if __name__ == "__main__":
    try:
        from backend.chunker import chunk_text
        from backend.parser import get_full_text
    except ImportError:
        from chunker import chunk_text
        from parser import get_full_text

    PDF_PATH = "/home/prashanna/Documents/AI_Research_Assistant/uploaded_papers/attention_is_all_you_need.pdf"
    full_text = get_full_text(PDF_PATH)
    chunks = chunk_text(full_text)

    embeddings = get_embeddings(chunks)
    print(f"Number of chunks: {len(chunks)}")
    print(f"Embedding dimension: {len(embeddings[0])}")
    print(f"First embedding preview: {embeddings[0][:5]}")