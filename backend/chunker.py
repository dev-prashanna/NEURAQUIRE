def chunk_text(text:str,chunk_size: int =500, overlap: int= 50) -> list:
    import re
    sentences=re.split(r'(?<=[.!?])\s+',text)
    current_chunk=[]
    current_length=0
    words=text.split()
    chunks=[]
    step=chunk_size-overlap
    for i in range(0,len(words),step):
        chunk_words=words[i:i+chunk_size]
        chunk_text=" ".join(chunk_words)
        chunks.append(chunk_text)


    return chunks
if __name__ == "__main__":
    try:
        from backend.parser import get_full_text
    except ImportError:
        from parser import get_full_text

    PDF_PATH = "/home/prashanna/Documents/AI_Research_Assistant/uploaded_papers/attention_is_all_you_need.pdf"
    full_text = get_full_text(PDF_PATH)

    chunks = chunk_text(full_text)
    print(f"Total chunks: {len(chunks)}")
    print(f"First chunk preview: {chunks[0][:200]}")







    