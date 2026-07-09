import streamlit as st
import os
import re

st.set_page_config(page_title="NeuraQuire", page_icon=":robot_face:", layout="wide")
st.title("NeuraQuire")

api_key = st.sidebar.text_input(
    "MiMo API Key",
    type="password",
    help="Enter your MiMo API key. Get it from https://platform.xiaomimimo.com/console/api-keys"
)

if not api_key:
    st.warning("Please enter your MiMo API key in the sidebar to use the app.")
    st.stop()

uploaded_file = st.sidebar.file_uploader("Upload a PDF", type=["pdf"])

if not uploaded_file:
    st.warning("Please upload a PDF file to use the app.")
    st.stop()

upload_dir = "uploaded_papers"
os.makedirs(upload_dir, exist_ok=True)
file_path = os.path.join(upload_dir, uploaded_file.name)
with open(file_path, "wb") as f:
    f.write(uploaded_file.getbuffer())

tab1, tab2, tab3, tab4 = st.tabs(["RAG Q&A", "Summarizer", "Comparator", "PDF Viewer"])

with tab1:
    st.header("Ask questions about your PDF")

    if "document" not in st.session_state:
        with st.spinner("Processing PDF..."):
            from backend.rag import load_document
            st.session_state.document = load_document(file_path)
        st.success(f"Loaded {len(st.session_state.document['chunks'])} chunks")

    question = st.text_input("Ask a question about the Paper:")
    if question:
        with st.spinner("Searching and generating answer..."):
            from backend.rag import ask_question, call_llm
            prompt, results = ask_question(st.session_state.document, question)
            answer = call_llm(prompt, api_key)

        st.subheader("Answer:")
        clean_answer =re.sub(r'<[^>]+>','',answer)
        st.write(clean_answer)

        with st.expander("See source chunks"):
            for i, r in enumerate(results):
                st.write(f"**Chunk {i + 1}** (similarity: {r['distance']:.4f})")
                st.write(r['chunk'][:300])
                st.write("---")

with tab2:
    st.header("Summarize your PDF")

    if st.button("Generate Summary"):
        with st.spinner("Summarizing... This may take a minute"):
            from backend.summarizer import summarize
            summary = summarize(file_path, api_key)

        st.subheader("Summary:")
        st.write(summary)

with tab3:
    st.header("Compare two PDFs")

    uploaded_file2 = st.file_uploader("Upload second PDF", type=["pdf"], key="second_pdf")

    if uploaded_file2 and st.button("Compare"):
        file_path2 = os.path.join(upload_dir, uploaded_file2.name)
        with open(file_path2, "wb") as f:
            f.write(uploaded_file2.getbuffer())

        with st.spinner("Comparing papers..."):
            from backend.comparator import compare_papers
            comparison = compare_papers(file_path, file_path2, api_key)

        st.subheader("Comparison:")
        st.write(comparison)

with tab4:
    st.header("View your PDF")

    from backend.parser import get_full_text, parse_pdf

    doc_data = parse_pdf(file_path)
    full_text = get_full_text(file_path)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Metadata")
        st.json(doc_data["metadata"])

    with col2:
        st.subheader("Text Preview")
        st.text_area("Full text", full_text[:2000], height=400)
