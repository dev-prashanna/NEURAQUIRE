import fitz

def parse_pdf(file_path: str):
    doc = fitz.open(file_path)

    result={
        "metadata":doc.metadata,
        "page_count":len(doc),
        "pages":[]
    }

    for page_num in range(len(doc)):
        page=doc[page_num]
        text=page.get_text()
        result["pages"].append({
            "page_number": page_num+1,
            "text":text
        })
        print(f"--- Page {page_num + 1} ---")
        print(text)
    doc.close()
    return result


def get_full_text(file_path: str) -> str:
    doc = fitz.open(file_path)
    full_text = ""
    for page_num in range(len(doc)):
        page = doc[page_num]
        full_text += page.get_text()
    doc.close()
    return full_text

def extract_tables(file_path: str):
    doc = fitz.open(file_path)
    all_tables = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        tables = page.find_tables()

        if tables:
            page_tables = []
            for table in tables:
                data = table.extract()
                page_tables.append(data)

            all_tables.append({
                "page_number": page_num + 1,
                "tables": page_tables
            })

    doc.close()
    return all_tables

if __name__ == "__main__":
    PDF_PATH = "/home/prashanna/Documents/AI_Research_Assistant/uploaded_papers/attention_is_all_you_need.pdf"

    data = parse_pdf(PDF_PATH)
    print(f"Title: {data['metadata'].get('title', 'N/A')}")
    print(f"Pages: {data['page_count']}")
    print(f"First page text preview: {data['pages'][0]['text'][:200]}")

    full_text = get_full_text(PDF_PATH)
    print(f"\nFull text length: {len(full_text)} characters")
    print(f"Preview: {full_text[:300]}")

    tables = extract_tables(PDF_PATH)
    print(f"\nFound tables on {len(tables)} pages")
    for t in tables:
        print(f"Page {t['page_number']}: {len(t['tables'])} table(s)")