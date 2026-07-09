try:
    from backend.parser import parse_pdf, get_full_text
    from backend.chunker import chunk_text
    from backend.embeddings import get_embeddings
    from backend.vector_store import build_index, search
    from backend.prompts import build_prompt
except ImportError:
    from parser import parse_pdf, get_full_text
    from chunker import chunk_text
    from embeddings import get_embeddings
    from vector_store import build_index, search
    from prompts import build_prompt


def load_document(pdf_path: str) -> dict:
    full_text = get_full_text(pdf_path)
    chunks = chunk_text(full_text)
    embeddings = get_embeddings(chunks)
    index = build_index(embeddings)
    
    return {
        "index": index,
        "chunks": chunks,
        "metadata": parse_pdf(pdf_path)["metadata"]
    }

from sentence_transformers import SentenceTransformer

model = SentenceTransformer("all-MiniLM-L12-v2")


def ask_question(document: dict, question: str, top_k: int = 3) -> str:
    query_embedding = model.encode([question])[0].tolist()
    
    results = search(document["index"], query_embedding, document["chunks"], top_k=top_k)
    
    context_chunks = [r["chunk"] for r in results]
    
    prompt = build_prompt(question, context_chunks)
    
    return prompt, results

from openai import OpenAI


def call_llm(prompt: str, api_key: str) -> str:
    client = OpenAI(
        api_key=api_key,
        base_url="https://api.xiaomimimo.com/v1"
    )

    response = client.chat.completions.create(
        model="mimo-v2.5",
        messages=[
            {"role": "user", "content": prompt}
        ],
        max_tokens=1024,
        temperature=0.3
    )

    return response.choices[0].message.content


if __name__ == "__main__":
    import os
    PDF_PATH = "uploaded_papers/sample.pdf"
    API_KEY = os.getenv("OPENAI_API_KEY", "your-api-key-here")

    print("Loading document...")
    document = load_document(PDF_PATH)
    print(f"Loaded {len(document['chunks'])} chunks")

    question = "What is the transformer architecture?"
    print(f"\nQuestion: {question}")

    prompt, results = ask_question(document, question)
    print(f"\nTop {len(results)} relevant chunks found")
    for i, r in enumerate(results):
        print(f"\n  Chunk {i + 1} (similarity: {r['distance']:.4f}):")
        print(f"  {r['chunk'][:150]}...")

    print("\nGenerating answer...")
    answer = call_llm(prompt, API_KEY)
    print(f"\nAnswer:\n{answer}")