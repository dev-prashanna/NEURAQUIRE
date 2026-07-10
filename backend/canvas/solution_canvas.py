import streamlit as st
import re
import logging

logger = logging.getLogger(__name__)


def render_solution_canvas(steps:list = None, on_step_click=None):
  st.subheader(" Solution Canvas")

  if steps:
    _render_steps(steps, on_step_click)
  else:
    _render_empty_state()


def _render_empty_state():
  st.markdown("""
  <div style="
    text-align:center;
    padding:40px 20px;
    color:#666;
    border:2px dashed #ddd;
    border-radius:10px;
    margin:20px 0;
  ">
    <p style="font-size:24px; margin-bottom:10px;"></p>
    <p style="font-size:16px; font-weight:bold;">Solution Canvas</p>
    <p style="font-size:14px;">Enter a math problem to see step-by-step solutions here</p>
  </div>
  """, unsafe_allow_html=True)


def _render_steps(steps:list, on_step_click=None):
  for step in steps:
    _render_single_step(step, on_step_click)


def _render_single_step(step, on_step_click=None):
  step_colors = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7", "#DDA0DD", "#98D8C8"]
  color = step_colors[(step.step_number - 1) % len(step_colors)]

  with st.container():
    col1, col2 = st.columns([5, 1])
    with col1:
      st.markdown(f"**Step {step.step_number}:{step.title}**")
    with col2:
      if st.button("", key=f"locate_{step.step_number}", help="Locate in PDF"):
        if on_step_click:
          on_step_click(step)
        else:
          st.session_state[f"locate_step_{step.step_number}"] = True

    st.markdown(f"<div style='border-left:4px solid {color}; padding-left:12px; margin:8px 0;'>{step.explanation}</div>", unsafe_allow_html=True)

    if step.math_content:
      try:
        st.markdown(f"$$\n{step.math_content}\n$$")
      except Exception:
        st.code(step.math_content, language="latex")

    with st.expander(" Teaching Note", expanded=False):
      if step.pedagogical_note:
        st.info(step.pedagogical_note)
      else:
        st.info("This step involves applying mathematical principles to simplify the problem.")

    if step.code_snippet:
      with st.expander(" Python Verification", expanded=False):
        st.code(step.code_snippet, language="python")

    st.divider()


def render_problem_input() -> tuple[str, str]:
  st.subheader(" Problem Input")

  problem = st.text_area(
    "Enter your math problem:",
    height=120,
    key="math_problem_input",
    placeholder="e.g., Find the integral of x² * e^x dx",
    help="Type or paste a math problem. You can use LaTeX notation."
  )

  col1, col2 = st.columns(2)
  with col1:
    difficulty = st.select_slider(
      "Difficulty Level",
      options=["Grade 12", "Undergrad", "Graduate"],
      value="Grade 12",
      key="difficulty_slider"
    )
  with col2:
    show_code = st.checkbox("Show Python verification", value=True, key="show_code")

  return problem, difficulty.lower().replace(" ", "_"), show_code


def render_solution_controls():
  col1, col2, col3 = st.columns(3)

  with col1:
    if st.button(" Clear Solution", key="clear_solution"):
      st.session_state.solution_steps = []
      st.rerun()

  with col2:
    if st.button(" Copy Solution", key="copy_solution"):
      steps = st.session_state.get("solution_steps", [])
      if steps:
        text = "\n\n".join([
          f"Step {s.step_number}:{s.title}\n{s.explanation}\n{s.math_content}"
          for s in steps
        ])
        st.code(text, language=None)

  with col3:
    if st.button(" Practice Problems", key="gen_practice"):
      st.session_state.generate_practice = True


def render_final_answer(answer:str):
  if answer:
    st.markdown("---")
    st.markdown("**Final Answer:**")
    try:
      st.markdown(f"$$\n\\boxed{{{answer}}}\n$$")
    except Exception:
      st.markdown(f"**{answer}**")


def render_practice_problems(problems:list[str]):
  if problems:
    st.markdown("---")
    st.subheader(" Practice Problems")

    for i, problem in enumerate(problems, 1):
      with st.expander(f"Problem {i}", expanded=False):
        st.markdown(problem)
