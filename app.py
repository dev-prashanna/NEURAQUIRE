import streamlit as st
import os
import re
import tempfile
from backend.logging_config import setup_logging, log_event
from backend.config import load_env_file
load_env_file()
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

app_mode = st.sidebar.selectbox(
    "Mode",
    ["Standard Chat", "Math Wizard"],
    key="app_mode"
)


def render_standard_chat():
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
                        for i, r in enumerate(msg.sources):
                            st.write(f"**Chunk {i+1}** (similarity: {r['distance']:.4f})")
                            st.write(r['chunk'][:300])
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


def render_math_wizard():
    from backend.math_wizard.analyzer import MathAnalyzer, MathContext
    from backend.math_wizard.annotator import PDFAnnotator, Annotation
    from backend.math_wizard.solver import MathSolver, SolutionStep, DifficultyLevel
    from backend.math_wizard.synchronizer import MathWizardSynchronizer
    from backend.math_wizard.prompts import build_solver_prompt
    from backend.math_wizard.export import AnnotatedPDFExporter
    from backend.canvas.pdf_viewer import render_pdf_canvas, render_pdf_toolbar
    from backend.canvas.solution_canvas import (
        render_solution_canvas, render_problem_input,
        render_solution_controls, render_final_answer, render_practice_problems
    )
    from backend.canvas.annotation_layer import AnnotationLayer
    from backend.canvas.vlm_panel import render_vlm_panel

    if "math_state" not in st.session_state:
        st.session_state.math_state = {
            "annotator": None,
            "analyzer": MathAnalyzer(),
            "synchronizer": MathWizardSynchronizer(),
            "annotation_layer": AnnotationLayer(),
            "math_context": None,
            "solution_steps": [],
            "final_answer": "",
            "practice_problems": [],
            "selected_color": "#FFFF00"
        }

    math_state = st.session_state.math_state

    if math_state["annotator"] is None:
        math_state["annotator"] = PDFAnnotator(file_path)

    if math_state["math_context"] is None:
        with st.spinner("🔍 Analyzing mathematical content in document..."):
            try:
                math_state["math_context"] = math_state["analyzer"].analyze_document(file_path)
                formulas = math_state["math_context"].formulas
                math_state["annotator"].mark_formulas(formulas)
                log_event("MATH_ANALYSIS", user_id, {
                    "formulas_found": len(formulas),
                    "topics": math_state["math_context"].topics
                })
            except Exception as e:
                logger.error(f"Math analysis failed: {e}")
                st.warning("Could not analyze mathematical content. You can still use Math Wizard.")

    st.subheader("🔢 Math Wizard")

    with st.expander("📊 Document Analysis", expanded=False):
        if math_state["math_context"]:
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Formulas Found", len(math_state["math_context"].formulas))
            with col2:
                st.metric("Topics", ", ".join(math_state["math_context"].topics[:3]))

            if math_state["math_context"].formulas:
                st.markdown("**Key Formulas:**")
                for f in math_state["math_context"].formulas[:5]:
                    st.markdown(f"- ${f.latex[:50]}$")
        else:
            st.info("No mathematical content detected in this document.")

    vlm_tab, main_tab = st.tabs(["👁️ Vision Analysis", "📐 Main Canvas"])

    with vlm_tab:
        render_vlm_panel(file_path, api_key)

    with main_tab:
     left_col, right_col = st.columns([1, 1])

    with left_col:
        st.markdown("**📄 Document Viewer**")
        all_annotations = math_state["annotator"].get_all_annotations()
        render_pdf_canvas(file_path, annotations=all_annotations)
        render_pdf_toolbar()

        with st.expander("🎨 Annotation Tools", expanded=False):
            color_options = {
                "Yellow (Highlight)": "#FFFF00",
                "Green (Correct)": "#00FF00",
                "Red (Important)": "#FF0000",
                "Blue (Note)": "#0000FF",
                "Orange (Warning)": "#FFA500"
            }
            selected_color_name = st.selectbox(
                "Annotation Color",
                list(color_options.keys()),
                key="annotation_color"
            )
            math_state["selected_color"] = color_options[selected_color_name]

            if st.button("🗑️ Clear All Annotations", key="clear_annotations"):
                math_state["annotator"] = PDFAnnotator(file_path)
                math_state["annotation_layer"].clear_annotations()
                st.rerun()

    with right_col:
        st.markdown("**🧮 Solution Canvas**")

        render_solution_canvas(
            steps=math_state["solution_steps"],
            on_step_click=lambda step: math_state["synchronizer"].sync_hover_effect(step)
        )

        problem, difficulty, show_code = render_problem_input()

        if st.button("🚀 Solve Problem", type="primary", key="solve_button"):
            if problem:
                with st.spinner("🧠 Solving problem..."):
                    try:
                        llm_client = _get_llm_client(api_key)

                        solver = MathSolver(llm_client, math_state["analyzer"])
                        history = st.session_state.conversation.get_context(include_last_n=3)

                        steps = solver.solve_problem(
                            problem=problem,
                            context=math_state["math_context"],
                            difficulty=DifficultyLevel(difficulty),
                            history=history
                        )

                        math_state["solution_steps"] = steps

                        if steps:
                            math_state["final_answer"] = steps[-1].math_content if steps[-1].math_content else ""

                        for step in steps:
                            if step.highlight_regions:
                                math_state["synchronizer"].sync_step_to_pdf(step)

                        log_event("MATH_SOLVED", user_id, {
                            "problem": problem[:100],
                            "steps": len(steps)
                        })

                    except Exception as e:
                        logger.error(f"Math solving failed: {e}")
                        st.error(f"Failed to solve problem: {e}")

        render_solution_controls()

        if math_state["solution_steps"]:
            render_final_answer(math_state["final_answer"])

        if math_state["practice_problems"]:
            render_practice_problems(math_state["practice_problems"])

        if st.session_state.get("generate_practice"):
            if math_state["solution_steps"]:
                with st.spinner("Generating practice problems..."):
                    try:
                        llm_client = _get_llm_client(api_key)
                        solver = MathSolver(llm_client, math_state["analyzer"])
                        problems = solver.generate_practice_variations(
                            problem,
                            math_state["solution_steps"]
                        )
                        math_state["practice_problems"] = problems
                        st.session_state.generate_practice = False
                    except Exception as e:
                        logger.error(f"Practice generation failed: {e}")
                        st.error("Failed to generate practice problems.")

        st.divider()

        if math_state["solution_steps"]:
            st.markdown("**📥 Export Options**")

            export_col1, export_col2 = st.columns(2)

            with export_col1:
                if st.button("📄 Export Annotated PDF", key="export_annotated"):
                    try:
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                            tmp_path = tmp.name

                        exporter = AnnotatedPDFExporter(file_path)

                        if math_state["solution_steps"]:
                            exporter.add_solution_overlay(math_state["solution_steps"])

                        if math_state["math_context"]:
                            exporter.add_formula_glossary(math_state["math_context"].formulas)

                        exporter.add_metadata_page(
                            problem,
                            math_state["solution_steps"],
                            math_state["final_answer"]
                        )

                        output_path = tmp_path.replace(".pdf", "_annotated.pdf")
                        exporter.export(output_path)
                        exporter.close()

                        with open(output_path, "rb") as f:
                            pdf_bytes = f.read()

                        st.download_button(
                            label="⬇️ Download Annotated PDF",
                            data=pdf_bytes,
                            file_name=f"math_wizard_annotated.pdf",
                            mime="application/pdf"
                        )

                        log_event("PDF_EXPORTED", user_id, {"output": output_path})

                    except Exception as e:
                        logger.error(f"Export failed: {e}")
                        st.error(f"Failed to export PDF: {e}")

            with export_col2:
                if st.button("📋 Copy Solution", key="copy_solution_text"):
                    solution_text = "\n\n".join([
                        f"**Step {s.step_number}: {s.title}**\n{s.explanation}\n${s.math_content}$"
                        for s in math_state["solution_steps"]
                    ])
                    st.code(solution_text, language=None)

    if st.session_state.conversation:
        st.divider()
        with st.expander("💬 Chat History", expanded=False):
            for msg in st.session_state.conversation.get_all():
                role = "🧑" if msg.role == "user" else "🤖"
                st.markdown(f"**{role} {msg.role.title()}:** {msg.content[:200]}")


def _get_llm_client(api_key: str):
    from openai import OpenAI
    from backend.config import settings

    return OpenAI(
        api_key=api_key,
        base_url=settings.LLM_BASE_URL
    )


if app_mode == "Standard Chat":
    render_standard_chat()
elif app_mode == "Math Wizard":
    render_math_wizard()
