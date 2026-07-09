import fitz
import os 

def parse_pdf(file_path: str) -> dict:
    with fitz.open(file_path) as doc:
        result = {
            "metadata": doc.metadata,
            "page_count": len(doc),
            "pages": []
        }

        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            result["pages"].append({
                "page_number": page_num + 1,
                "text": text
            })

    return result


def get_full_text(file_path: str) -> str:
    with fitz.open(file_path) as doc:
        full_text = ""
        for page_num in range(len(doc)):
            page = doc[page_num]
            full_text += page.get_text()

    return full_text


def extract_tables(file_path: str) -> list:
    with fitz.open(file_path) as doc:
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

    return all_tables

def extract_images(file_path:str,output_dir:str) -> list:
    os.makedirs(output_dir, exist_ok=True)

    with fitz.open(file_path) as doc:
        all_images=[]

        for page_num in range(len(doc)):
            page=doc[page_num]
            images=page.get_images()

            for img in images:
                xref=img[0]
                base_image=doc.extract_image(xref)
                image_bytes=base_image["image"]
                ext=base_image["ext"]
                img_width=base_image["width"]
                img_height=base_image["height"]

                img_filename=f"page{page_num+1}_img{xref}.{ext}"
                img_path=os.path.join(output_dir,img_filename)

                with open(img_path,"wb") as f:
                    f.write(image_bytes)

                all_images.append({
                    "page_number": page_num+1,
                    "image_path": img_path,
                    "width": img_width,
                    "height": img_height,
                })

    return all_images


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

    images = extract_images(PDF_PATH, "extracted_images")
    print(f"\nExtracted {len(images)} images")
    for img in images:
        print(f"  Page {img['page_number']}: {img['image_path']} ({img['width']}x{img['height']})")