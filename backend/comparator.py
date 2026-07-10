from openai import OpenAI
from backend.parser import get_full_text
from backend.security import llm_rate_limiter
from backend.rag import RateLimitExceeded
from backend.config import settings


def build_comparison_prompt(text1: str, text2: str) -> str:
    return f"""Compare these two research papers. Provide:
1. Key similarities
2. Key differences
3. Unique contributions of each paper

Paper 1:
{text1}

Paper 2:
{text2}

Comparison:"""


def compare_papers(pdf_path1: str, pdf_path2: str, api_key: str, user_id: str = "anonymous") -> str:
    allowed, retry_after = llm_rate_limiter.allow(user_id)
    if not allowed:
        raise RateLimitExceeded(
            f"Rate limit exceeded. Try again in {retry_after:.0f} seconds."
        )

    text1 = get_full_text(pdf_path1)
    text2 = get_full_text(pdf_path2)

    text1 = text1[:10000]
    text2 = text2[:10000]

    prompt = build_comparison_prompt(text1, text2)

    client = OpenAI(
        api_key=api_key,
        base_url=settings.LLM_BASE_URL
    )

    response = client.chat.completions.create(
        model=settings.LLM_MODEL,
        messages=[
            {"role": "user", "content": prompt}
        ],
        max_tokens=2048,
        temperature=settings.LLM_TEMPERATURE
    )

    return response.choices[0].message.content


if __name__ == "__main__":
    import os
    API_KEY = os.getenv("OPENAI_API_KEY", "your-api-key-here")

    pdf1 = "uploaded_papers/paper1.pdf"
    pdf2 = "uploaded_papers/paper2.pdf"

    print("Comparing papers...")
    result = compare_papers(pdf1, pdf2, API_KEY)
    print(f"\n{result}")