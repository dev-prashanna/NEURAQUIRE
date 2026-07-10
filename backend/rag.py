from backend.parser import parse_pdf, get_full_text, PDFError
from backend.chunker import chunk_text
from backend.embeddings import get_embeddings
from backend.vector_store import build_index, search
from backend.prompts import build_prompt
from backend.security import llm_rate_limiter, llm_cost_tracker
from backend.model_manager import model_manager
from backend.config import settings
import logging

logger = logging.getLogger(__name__)


class RateLimitExceeded(Exception):
    pass


class LLMError(Exception):
    pass


class ModelLoadError(Exception):
    pass


def load_document(pdf_path: str) -> dict:
    try:
        full_text = get_full_text(pdf_path)
    except PDFError:
        raise
    except Exception as e:
        logger.error(f"Failed to load document {pdf_path}: {e}")
        raise PDFError(f"Cannot process this PDF. It may be corrupt or unreadable.") from e

    if not full_text.strip():
        raise PDFError("PDF contains no extractable text. It may be a scanned document.")

    chunks = chunk_text(full_text, chunk_size=settings.CHUNK_SIZE, overlap=settings.CHUNK_OVERLAP)
    if not chunks:
        raise PDFError("Failed to split document into chunks.")

    try:
        embeddings = get_embeddings(chunks)
    except Exception as e:
        logger.error(f"Failed to generate embeddings: {e}")
        raise ModelLoadError("Failed to load AI model. Please try again.") from e

    index = build_index(embeddings)

    return {
        "index": index,
        "chunks": chunks,
        "metadata": parse_pdf(pdf_path)["metadata"]
    }


def ask_question(document: dict, question: str, top_k: int = None, history: list = None) -> str:
    if top_k is None:
        top_k = settings.TOP_K_RESULTS

    try:
        query_embedding = model_manager.encode_single(question)
    except Exception as e:
        logger.error(f"Failed to encode question: {e}")
        raise ModelLoadError("Failed to process question. Please try again.") from e

    results = search(document["index"], query_embedding, document["chunks"], top_k=top_k)

    context_chunks = [r["chunk"] for r in results]

    prompt = build_prompt(question, context_chunks, history=history)

    return prompt, results


from openai import OpenAI


def call_llm(prompt: str, api_key: str, user_id: str = "anonymous") -> str:
    allowed, retry_after = llm_rate_limiter.allow(user_id)
    if not allowed:
        raise RateLimitExceeded(
            f"Rate limit exceeded. Try again in {retry_after:.0f} seconds. "
            f"Remaining requests: {llm_rate_limiter.remaining(user_id)}"
        )

    client = OpenAI(
        api_key=api_key,
        base_url=settings.LLM_BASE_URL
    )

    try:
        response = client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[
                {"role": "user", "content": prompt}
            ],
            max_tokens=settings.LLM_MAX_TOKENS,
            temperature=settings.LLM_TEMPERATURE
        )
    except Exception as e:
        logger.error(f"LLM API call failed: {e}")
        raise LLMError("Failed to get response from AI model. Please try again.") from e

    usage = response.usage
    if usage:
        llm_cost_tracker.record(user_id, usage.total_tokens)

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