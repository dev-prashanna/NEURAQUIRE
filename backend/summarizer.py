from openai import OpenAI
from backend.parser import get_full_text
from backend.chunker import chunk_text
from backend.security import llm_rate_limiter, llm_cost_tracker
from backend.rag import RateLimitExceeded
from backend.config import settings


def summarize(pdf_path: str, api_key: str, user_id: str = "anonymous") -> str:
    full_text = get_full_text(pdf_path)
    chunks = chunk_text(full_text, chunk_size=1000, overlap=100)

    allowed, retry_after = llm_rate_limiter.allow(user_id)
    if not allowed:
        raise RateLimitExceeded(
            f"Rate limit exceeded. Try again in {retry_after:.0f} seconds."
        )

    client = OpenAI(
        api_key=api_key,
        base_url=settings.LLM_BASE_URL
    )

    summaries = []
    for i, chunk in enumerate(chunks):
        allowed, retry_after = llm_rate_limiter.allow(user_id)
        if not allowed:
            raise RateLimitExceeded(
                f"Rate limit exceeded during summarization at chunk {i+1}. "
                f"Try again in {retry_after:.0f} seconds."
            )

        response = client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[
                {"role": "user", "content": f"Summarize the following text in 2-3 sentences:\n\n{chunk}"}
            ],
            max_tokens=300,
            temperature=settings.LLM_TEMPERATURE
        )
        summaries.append(response.choices[0].message.content)

    combined = "\n\n".join(summaries)

    response = client.chat.completions.create(
        model=settings.LLM_MODEL,
        messages=[
            {"role": "user", "content": f"Write a comprehensive summary of this research paper based on these section summaries:\n\n{combined}"}
        ],
        max_tokens=settings.LLM_MAX_TOKENS,
        temperature=settings.LLM_TEMPERATURE
    )

    return response.choices[0].message.content


if __name__ == "__main__":
    import os
    PDF_PATH = "uploaded_papers/sample.pdf"
    API_KEY = os.getenv("OPENAI_API_KEY", "your-api-key-here")

    print("Summarizing...")
    summary = summarize(PDF_PATH, API_KEY)
    print(f"\nSummary:\n{summary}")