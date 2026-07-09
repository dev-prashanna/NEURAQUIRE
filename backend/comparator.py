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
from openai import OpenAI
try:
    from backend.parser import get_full_text
except ImportError:
    from parser import get_full_text


def compare_papers(pdf_path1: str, pdf_path2: str, api_key: str) -> str:
    text1 = get_full_text(pdf_path1)
    text2 = get_full_text(pdf_path2)

    # Truncate to fit context window (MiMo V2.5 supports 1M tokens, so we're safe)
    # But keep it reasonable for speed
    text1 = text1[:10000]
    text2 = text2[:10000]

    prompt = build_comparison_prompt(text1, text2)

    client = OpenAI(
        api_key=api_key,
        base_url="https://api.xiaomimimo.com/v1"
    )

    response = client.chat.completions.create(
        model="mimo-v2.5",
        messages=[
            {"role": "user", "content": prompt}
        ],
        max_tokens=2048,
        temperature=0.3
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