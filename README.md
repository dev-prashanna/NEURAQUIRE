# NeuraQuire

[![Python](https://img.shields.io/badge/Python-3.10+-yellow)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![LangChain](https://img.shields.io/badge/LangChain-0.1+-orange)](https://www.langchain.com/)
[![OpenAI](https://img.shields.io/badge/OpenAI-API-412991)](https://openai.com/)

RAG-powered research assistant with PDF parsing, semantic chunking, and LLM query pipeline.

## Overview

NeuraQuire is a tool for researchers to interact with academic papers using Retrieval-Augmented Generation (RAG). Upload PDF papers, extract structured content (text, tables, images), chunk documents semantically, generate embeddings, and query papers using natural language.

The system processes research papers through a multi-stage pipeline:

1. **PDF Parsing** -- Extract text, tables, and images from academic papers
2. **Semantic Chunking** -- Split documents into context-aware segments
3. **Embedding Generation** -- Create vector representations using sentence transformers
4. **Vector Storage** -- Index embeddings for efficient similarity search
5. **RAG Query** -- Retrieve relevant context and generate answers via LLM

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│    PDF Input    │────>│     Parser      │────>│    Chunker      │
│  (PyMuPDF)      │     │  (text/tables/  │     │  (sliding window│
│                 │     │   images)       │     │   + overlap)    │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                        │
                                                        v
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   LLM Query     │<────│    Retriever    │<────│   Embeddings    │
│  (OpenAI GPT)   │     │  (similarity    │     │  (sentence-     │
│                 │     │   search)       │     │   transformers) │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        │                                               │
        v                                               v
┌─────────────────┐                         ┌─────────────────┐
│     Answer      │                         │   Vector DB     │
│  (generated)    │                         │    (FAISS)      │
└─────────────────┘                         └─────────────────┘
```

## Project Structure

```
NEURAQUIRE/
├── backend/
│   ├── __init__.py
│   ├── parser.py              # PDF parsing (text, tables, images)
│   ├── chunker.py             # Semantic text chunking
│   ├── embeddings.py          # Embedding generation
│   ├── vector_store.py        # Vector database operations
│   ├── rag.py                 # RAG query pipeline
│   ├── summarizer.py          # Document summarization
│   ├── comparator.py          # Paper comparison
│   ├── prompts.py             # LLM prompt templates
│   ├── equation_extractor.py  # LaTeX equation extraction
│   ├── readability.py         # Text readability analysis
│   ├── future_ideas.py        # Future feature ideas
│   └── utils.py               # Utility functions
├── frontend/                  # Frontend application (planned)
├── models/                    # Model weights (gitignored)
├── uploaded_papers/           # User-uploaded PDFs (gitignored)
├── vector_db/                 # Vector database (gitignored)
├── app.py                     # Streamlit application entry point
├── requirements.txt           # Python dependencies
├── .gitignore                 # Git ignore rules
├── LICENSE                    # MIT License
└── README.md                  # This file
```

## Installation

### Prerequisites

- Python 3.10+
- pip or conda
- OpenAI API key (for LLM features)

### Setup

```bash
# Clone the repository
git clone https://github.com/dev-prashanna/NEURAQUIRE.git
cd NEURAQUIRE

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt
```

### Environment Variables

Create a `.env` file in the project root:

```env
OPENAI_API_KEY=your-api-key-here
```

## Usage

### Streamlit Web Interface

```bash
streamlit run app.py
```

This will launch the web interface where you can:
- Upload PDF papers
- Ask questions about the paper (RAG Q&A)
- Generate summaries
- Compare two papers
- View PDF metadata and text

### PDF Parsing

```python
from backend.parser import parse_pdf, get_full_text, extract_tables, extract_images

# Parse PDF with metadata
data = parse_pdf("paper.pdf")
print(f"Title: {data['metadata'].get('title', 'N/A')}")
print(f"Pages: {data['page_count']}")

# Get full text
text = get_full_text("paper.pdf")

# Extract tables
tables = extract_tables("paper.pdf")

# Extract images
images = extract_images("paper.pdf", "output_dir/")
```

### Text Chunking

```python
from backend.chunker import chunk_text

# Chunk text with overlap
chunks = chunk_text(full_text, chunk_size=500, overlap=50)
print(f"Total chunks: {len(chunks)}")
```

### RAG Query

```python
from backend.rag import load_document, ask_question, call_llm

# Load document and build index
document = load_document("paper.pdf")

# Ask questions
prompt, results = ask_question(document, "What are the main contributions?")
answer = call_llm(prompt, api_key)
print(answer)
```

## Features

| Feature | Status | Description |
|---------|--------|-------------|
| PDF Parsing | Complete | Extract text, metadata, tables, images from PDFs |
| Text Chunking | Complete | Split documents with configurable chunk size and overlap |
| Embedding Generation | Complete | Vector representations using sentence transformers |
| Vector Store | Complete | FAISS-based similarity search |
| RAG Query | Complete | Natural language queries over paper content |
| Summarization | Complete | Auto-generate paper summaries |
| Paper Comparison | Complete | Compare findings across multiple papers |
| Web Interface | Complete | Streamlit-based frontend |
| Equation Extraction | Planned | Extract and render LaTeX equations |

## Technical Details

### Parser

Uses PyMuPDF (fitz) for high-fidelity PDF extraction:
- Text extraction with page-level granularity
- Table detection and structured extraction
- Image extraction with metadata (dimensions, location)

### Chunker

Implements sliding-window chunking:
- Configurable chunk size (default: 500 words)
- Overlap between chunks for context continuity (default: 50 words)
- Sentence-boundary aware splitting

### Embeddings

Uses sentence-transformers with all-MiniLM-L12-v2 model:
- 384-dimensional embeddings
- Optimized for semantic similarity search

### Vector Store

FAISS-based vector database:
- Normalized inner product similarity
- Efficient nearest neighbor search

## Results

| Metric | Value |
|--------|-------|
| PDF Parsing Speed | ~2 seconds/page |
| Chunk Size | 500 words (configurable) |
| Embedding Dimension | 384 (all-MiniLM-L12-v2) |

## Future Work

- [ ] Add equation extraction and rendering
- [ ] Implement citation tracking across papers
- [ ] Support more LLM providers
- [ ] Add batch processing for multiple papers
- [ ] Create REST API for programmatic access
- [ ] Add user authentication and paper management

## References

- Lewis et al. (2020). Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks. *NeurIPS*.
- Khattab & Zaharia (2020). ColBERT: Efficient and Effective Passage Search via Contextualized Late Interaction over BERT. *SIGIR*.
- [PyMuPDF Documentation](https://pymupdf.readthedocs.io/)
- [Sentence Transformers Documentation](https://www.sbert.net/)
- [LangChain Documentation](https://docs.langchain.com/)

## Citation

If you use this work in your research, please cite:

```bibtex
@article{tiwari2026neuraquire,
  title={NeuraQuire: RAG-powered Research Paper Analysis},
  author={Tiwari, Prashanna},
  year={2026},
  url={https://github.com/dev-prashanna/NEURAQUIRE}
}
```

## License

This project is licensed under the MIT License -- see the [LICENSE](LICENSE) file for details.

## Author

**Prashanna Tiwari**
- GitHub: [@dev-prashanna](https://github.com/dev-prashanna)
- LinkedIn: [Prashanna Tiwari](https://www.linkedin.com/in/prashanna-tiwari-1b9a01398/)
