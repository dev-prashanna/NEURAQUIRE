import streamlit as st
import os
import re
from backend.logging_config import setup_logging, log_event
from backend.config import settings
from backend.security import (
    validate_file, generate_safe_filepath, llm_rate_limiter, llm_cost_tracker,
    sanitize_question, PromptInjectionDetected, cleanup_old_files, delete_file
)
from backend.rag import RateLimitExceeded, LLMError, ModelLoadError
from backend.parser import PDFError
from backend.conversation import ConversationHistory

setup_logging()
logger = __import__("logging").getLogger(__name__)

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

upload_dir = settings.UPLOAD_DIR
os.makedirs(upload_dir, exist_ok=True)

deleted_count = cleanup_old_files(upload_dir)
if deleted_count > 0:
    logger.info(f"Cleaned up {deleted_count} expired files")

user_id = st.session_state.get("user_id", "anonymous")
if "user_id" not in st.session_state:
    import uuid
    st.session_state.user_id = uuid.uuid4().hex[:8]
    user_id = st.session_state.user_id
    log_event("SESSION_START", user_id)

remaining = llm_rate_limiter.remaining(user_id)
st.sidebar.caption(f"API requests remaining: {remaining}/10")

is_valid, error_msg = validate_file(uploaded_file.name, uploaded_file.size)
if not is_valid:
    st.error(f"File rejected: {error_msg}")
    st.stop()

file_path = generate_safe_filepath(upload_dir, uploaded_file.name)
with open(file_path, "wb") as f:
    f.write(uploaded_file.getbuffer())

log_event("FILE_UPLOAD", user_id, {"file": uploaded_file.name, "size": uploaded_file.size, "path": file_path})

if "current_file" in st.session_state and st.session_state.current_file:
    old_file = st.session_state.current_file
    if os.path.exists(old_file) and old_file != file_path:
        delete_file(old_file)

st.session_state.current_file = file_path

if "conversation" not in st.session_state:
    st.session_state.conversation = ConversationHistory(max_turns=10)

tab1, tab2, tab3, tab4 = st.tabs(["Chat", "Summarizer", "Comparator", "PDF Viewer"])

with tab1:
    st.header("Chat with your PDF")

    if "document" not in st.session_state:
        with st.spinner("Processing PDF..."):
            from backend.rag import load_document
            try:
                st.session_state.document = load_document(file_path)
            except PDFError as e:
                st.error(f"Failed to process PDF: {e}")
                st.stop()
            except ModelLoadError as e:
                st.error(str(e))
                st.stop()
            except Exception as e:
                logger.error(f"Unexpected error loading document: {e}")
                st.error("An unexpected error occurred while processing the PDF.")
                st.stop()
        st.success(f"Loaded {len(st.session_state.document['chunks'])} chunks")

    conversation = st.session_state.conversation

    for msg in conversation.get_all():
        with st.chat_message(msg.role):
            st.write(msg.content)
            if msg.sources:
                with st.expander("Sources"):
                    for i, src in enumerate(msg.sources):
                        st.write(f"**Chunk {i+1}** (similarity: {src['distance']:.4f})")
                        st.write(src['chunk'][:300])
                        st.write("---")

    if prompt := st.chat_input("Ask a question about the paper..."):
        try:
            safe_question = sanitize_question(prompt)
        except PromptInjectionDetected as e:
            log_event("INJECTION_BLOCKED", user_id, {"question": prompt[:100]})
            st.error(str(e))
            st.stop()

        log_event("QUESTION_ASKED", user_id, {"question": safe_question[:100]})

        st.session_state.conversation.add_user_message(safe_question)
        with st.chat_message("user"):
            st.write(safe_question)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                from backend.rag import ask_question, call_llm
                history = conversation.get_context(include_last_n=3)
                try:
                    prompt_text, results = ask_question(
                        st.session_state.document, safe_question, history=history
                    )
                except ModelLoadError as e:
                    st.error(str(e))
                    st.stop()

                try:
                    answer = call_llm(prompt_text, api_key, user_id=user_id)
                except RateLimitExceeded as e:
                    st.error(str(e))
                    st.stop()
                except LLMError as e:
                    st.error(str(e))
                    st.stop()
                except Exception as e:
                    logger.error(f"LLM call failed: {e}")
                    st.error("Failed to generate answer. Please try again.")
                    st.stop()

            clean_answer = re.sub(r'<[^>]+>', '', answer)
            st.write(clean_answer)

            with st.expander("See source chunks"):
                for i, r in enumerate(results):
                    st.write(f"**Chunk {i + 1}** (similarity: {r['distance']:.4f})")
                    st.write(r['chunk'][:300])
                    st.write("---")

            st.session_state.conversation.add_assistant_message(clean_answer, sources=results)

        cost = llm_cost_tracker.total(user_id)
        st.caption(f"Session cost: ${cost:.4f}")

    if conversation:
        st.divider()
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("Clear History"):
                st.session_state.conversation.clear()
                st.rerun()
        with col2:
            st.caption(f"Conversation turns: {len(conversation) // 2}")

with tab2:
    st.header("Summarize your PDF")

    if st.button("Generate Summary"):
        with st.spinner("Summarizing... This may take a minute"):
            from backend.summarizer import summarize
            try:
                summary = summarize(file_path, api_key, user_id=user_id)
            except RateLimitExceeded as e:
                st.error(str(e))
                st.stop()
            except LLMError as e:
                st.error(str(e))
                st.stop()
            except Exception as e:
                logger.error(f"Summarization failed: {e}")
                st.error("Failed to generate summary. Please try again.")
                st.stop()

        st.subheader("Summary:")
        st.write(summary)

with tab3:
    st.header("Compare two PDFs")

    uploaded_file2 = st.file_uploader("Upload second PDF", type=["pdf"], key="second_pdf")

    if uploaded_file2 and st.button("Compare"):
        is_valid2, error_msg2 = validate_file(uploaded_file2.name, uploaded_file2.size)
        if not is_valid2:
            st.error(f"File rejected: {error_msg2}")
        else:
            file_path2 = generate_safe_filepath(upload_dir, uploaded_file2.name)
            with open(file_path2, "wb") as f:
                f.write(uploaded_file2.getbuffer())

            with st.spinner("Comparing papers..."):
                from backend.comparator import compare_papers
                try:
                    comparison = compare_papers(file_path, file_path2, api_key, user_id=user_id)
                except RateLimitExceeded as e:
                    st.error(str(e))
                    st.stop()
                except LLMError as e:
                    st.error(str(e))
                    st.stop()
                except Exception as e:
                    logger.error(f"Comparison failed: {e}")
                    st.error("Failed to compare papers. Please try again.")
                    st.stop()
                finally:
                    delete_file(file_path2)

            st.subheader("Comparison:")
            st.write(comparison)

with tab4:
    st.header("View your PDF")

    from backend.parser import get_full_text, parse_pdf

    try:
        doc_data = parse_pdf(file_path)
        full_text = get_full_text(file_path)
    except PDFError as e:
        st.error(f"Failed to read PDF: {e}")
        st.stop()
    except Exception as e:
        logger.error(f"PDF viewer failed: {e}")
        st.error("Failed to display PDF.")
        st.stop()

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Metadata")
        st.json(doc_data["metadata"])

    with col2:
        st.subheader("Text Preview")
        st.text_area("Full text", full_text[:2000], height=400)
