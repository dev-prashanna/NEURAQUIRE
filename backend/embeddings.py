from backend.model_manager import model_manager


def get_embeddings(chunks: list) -> list:
    embeddings = model_manager.encode(chunks)
    return embeddings


if __name__ == "__main__":
    from backend.chunker import chunk_text
    from backend.parser import get_full_text

    PDF_PATH = "uploaded_papers/sample.pdf"
    full_text = get_full_text(PDF_PATH)
    chunks = chunk_text(full_text)

    embeddings = get_embeddings(chunks)
    print(f"Number of chunks: {len(chunks)}")
    print(f"Embedding dimension: {len(embeddings[0])}")
    print(f"First embedding preview: {embeddings[0][:5]}")