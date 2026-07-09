SYSTEM_PROMPT = """You are a research assistant. Answer the user's question using ONLY the provided context. 
If the context doesn't contain enough information, say "I don't have enough information to answer this."
Do not make up information."""

def build_prompt(question: str, context_chunks: list) -> str:
    context = "\n\n---\n\n".join(context_chunks)
    
    prompt = f"""{SYSTEM_PROMPT}

CONTEXT:
{context}

QUESTION: {question}

ANSWER:"""
    return prompt