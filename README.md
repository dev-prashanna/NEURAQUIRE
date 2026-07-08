# AI Research Assistant

RAG-powered research assistant with PDF parsing, semantic chunking, and LLM query pipeline.

## Overview

AI Research Assistant is a tool for researchers to interact with academic papers using Retrieval-Augmented Generation (RAG). Upload PDF papers, extract structured content (text, tables, images), chunk documents semantically, generate embeddings, and query papers using natural language.

The system processes research papers through a multi-stage pipeline:

1. **PDF Parsing** -- Extract text, tables, and images from academic papers
2. **Semantic Chunking** -- Split documents into context-aware segments
3. **Embedding Generation** -- Create vector representations using sentence transformers
4. **Vector Storage** -- Index embeddings for efficient similarity search
5. **RAG Query** -- Retrieve relevant context and generate answers via LLM

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  PDF Input  │────>│   Parser    │────>│  Chunker    │
└─────────────┘     └─────────────┘     └─────────────┘
                                               │
                                               v
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  LLM Query  │<────│  Retriever  │<────│  Embeddings │
└─────────────┘     └─────────────┘     └─────────────┘
       │                                       │
       v                                       v
┌─────────────┐                         ┌─────────────┐
│   Answer    │                         │ Vector DB   │
└─────────────┘                         └─────────────┘
```

## Project Structure

```
AI_Research_Assistant/
├── backend/
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
├── app.py                     # Main application entry point
├── requirements.txt           # Python dependencies
├── LICENSE                    # MIT License
└── README.md                  # This file
```

## Installation

### Prerequisites

- Python 3.10+
- pip or conda

### Setup

```bash
# Clone the repository
git clone https://github.com/dev-prashanna/AI_Research_Assistant.git
cd AI_Research_Assistant

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

## Features

| Feature | Status | Description |
|---------|--------|-------------|
| PDF Parsing | Complete | Extract text, metadata, tables, images from PDFs |
| Text Chunking | Complete | Split documents with configurable chunk size and overlap |
| Embedding Generation | In Progress | Vector representations using sentence transformers |
| Vector Store | In Progress | FAISS-based similarity search |
| RAG Query | In Progress | Natural language queries over paper content |
| Summarization | Planned | Auto-generate paper summaries |
| Paper Comparison | Planned | Compare findings across multiple papers |
| Equation Extraction | Planned | Extract and render LaTeX equations |
| Web Interface | Planned | Flask-based frontend |

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

## Future Work

- [ ] Complete embedding pipeline with sentence-transformers
- [ ] Implement FAISS vector store for efficient retrieval
- [ ] Build RAG query interface with OpenAI integration
- [ ] Add document summarization using LLMs
- [ ] Create web interface with Flask
- [ ] Support multi-paper comparison queries
- [ ] Add equation extraction and rendering
- [ ] Implement citation tracking across papers

## References

- Lewis et al. (2020). Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks. *NeurIPS*.
- Khattab & Zaharia (2020). ColBERT: Efficient and Effective Passage Search via Contextualized Late Interaction over BERT. *SIGIR*.
- [PyMuPDF Documentation](https://pymupdf.readthedocs.io/)
- [Sentence Transformers Documentation](https://www.sbert.net/)

## License

This project is licensed under the MIT License -- see the [LICENSE](LICENSE) file for details.

## Author

**Prashanna Tiwari**
- GitHub: [@dev-prashanna](https://github.com/dev-prashanna)
- LinkedIn: [Prashanna Tiwari](https://www.linkedin.com/in/prashanna-tiwari-1b9a01398/)
