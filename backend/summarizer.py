from openai import OpenAI
try:
    from backend.parser import get_full_text
    from backend.chunker import chunk_text
except ImportError:
    from parser import get_full_text
    from chunker import chunk_text


def summarize(pdf_path: str, api_key: str) -> str:
    full_text = get_full_text(pdf_path)
    chunks = chunk_text(full_text, chunk_size=1000, overlap=100)

    client = OpenAI(
        api_key=api_key,
        base_url="https://api.xiaomimimo.com/v1"
    )

    summaries = []
    for i, chunk in enumerate(chunks):
        response = client.chat.completions.create(
            model="mimo-v2.5",
            messages=[
                {"role": "user", "content": f"Summarize the following text in 2-3 sentences:\n\n{chunk}"}
            ],
            max_tokens=300,
            temperature=0.3
        )
        summaries.append(response.choices[0].message.content)
        print(f"  Summarized chunk {i + 1}/{len(chunks)}")

    combined = "\n\n".join(summaries)

    response = client.chat.completions.create(
        model="mimo-v2.5",
        messages=[
            {"role": "user", "content": f"Write a comprehensive summary of this research paper based on these section summaries:\n\n{combined}"}
        ],
        max_tokens=1024,
        temperature=0.3
    )

    return response.choices[0].message.content
if __name__ == "__main__":
    import os
    PDF_PATH = "uploaded_papers/sample.pdf"
    API_KEY = os.getenv("OPENAI_API_KEY", "your-api-key-here")

    print("Summarizing...")
    summary = summarize(PDF_PATH, API_KEY)
    print(f"\nSummary:\n{summary}")