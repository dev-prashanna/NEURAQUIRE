import streamlit as st
import base64
from datetime import datetime


def render_vlm_panel(file_path:str, api_key:str):
  st.subheader(" Vision Analysis")

  from backend.math_wizard.vision import FigureExtractor, VisionDescriber
  from backend.math_wizard.vlm_reasoner import VLMReasoner

  if "vlm_figures" not in st.session_state:
    st.session_state.vlm_figures = None
  if "vlm_results" not in st.session_state:
    st.session_state.vlm_results = {}
  if "vlm_extractor" not in st.session_state:
    st.session_state.vlm_extractor = None

  col1, col2 = st.columns([1, 1])

  with col1:
    st.markdown("**Extract Figures**")
    min_size = st.slider("Minimum figure size (px)", 50, 300, 100, key="vlm_min_size")

    if st.button(" Scan PDF for Figures", type="primary", key="scan_figures"):
      with st.spinner("Scanning PDF for figures..."):
        try:
          extractor = FigureExtractor(file_path)
          figures = extractor.extract_figures(
            min_width=min_size,
            min_height=min_size
          )
          st.session_state.vlm_figures = figures
          st.session_state.vlm_extractor = extractor
          st.success(f"Found {len(figures)} figures")
        except Exception as e:
          st.error(f"Failed to scan PDF:{e}")

  with col2:
    if st.session_state.vlm_figures:
      st.markdown(f"**Found {len(st.session_state.vlm_figures)} figures**")
      selected_fig = st.selectbox(
        "Select a figure",
        options=range(len(st.session_state.vlm_figures)),
        format_func=lambda i:f"Figure {i+1} (Page {st.session_state.vlm_figures[i].page_number})",
        key="selected_figure"
      )

      if selected_fig is not None and selected_fig < len(st.session_state.vlm_figures):
        fig = st.session_state.vlm_figures[selected_fig]

        img_b64 = base64.b64encode(fig.image_bytes).decode()
        st.image(
          f"data:image/png;base64,{img_b64}",
          caption=f"Figure on page {fig.page_number}",
          width="stretch"
        )

        if fig.figure_type != "unknown":
          st.caption(f"Type:{fig.figure_type}")
        if fig.caption:
          st.caption(f"Caption:{fig.caption}")

  if st.session_state.vlm_figures and st.session_state.vlm_figures:
    st.divider()

    col1, col2 = st.columns([2, 1])

    with col1:
      user_question = st.text_area(
        "Ask about this figure:",
        height=80,
        key="vlm_question",
        placeholder="e.g., What does this graph show? Explain the trend."
      )

      difficulty = st.select_slider(
        "Explanation level",
        options=["Grade 12", "Undergrad", "Graduate"],
        value="Grade 12",
        key="vlm_difficulty"
      )

    with col2:
      st.markdown("**Analysis Options**")
      auto_describe = st.checkbox("Auto-describe on select", value=True, key="auto_describe")
      show_technical = st.checkbox("Show technical details", value=False, key="show_technical")

    if st.button(" Analyze Figure", type="primary", key="analyze_figure"):
      if not api_key:
        st.error("Please enter your MiMo API key in the sidebar.")
        return

      selected_fig = st.session_state.get("selected_figure", 0)
      if selected_fig is None or selected_fig >= len(st.session_state.vlm_figures):
        st.error("Please select a figure first.")
        return

      fig = st.session_state.vlm_figures[selected_fig]

      with st.spinner(" Gemini is describing the image..."):
        try:
          vision = VisionDescriber()
          description = vision.describe_math_figure(fig.image_bytes, fig.caption)
          st.session_state[f"desc_{fig.figure_id}"] = description
        except ValueError as e:
          st.error(str(e))
          return
        except Exception as e:
          st.error(f"Vision analysis failed:{e}")
          return

      with st.spinner(" MiMo is reasoning about the figure..."):
        try:
          reasoner = VLMReasoner(vision)
          result = reasoner.analyze_figure_with_reasoning(
            image_bytes=fig.image_bytes,
            surrounding_text=fig.caption,
            user_question=user_question,
            api_key=api_key,
            difficulty=difficulty.lower().replace(" ", "_")
          )
          st.session_state.vlm_results[fig.figure_id] = result
        except Exception as e:
          st.error(f"Reasoning failed:{e}")
          return

    for fig in st.session_state.vlm_figures:
      if fig.figure_id in st.session_state.vlm_results:
        result = st.session_state.vlm_results[fig.figure_id]

        with st.expander(f" Analysis:Figure on Page {fig.page_number}", expanded=True):
          tab1, tab2, tab3 = st.tabs(["Reasoning", "Math Explanation", "Teaching Notes"])

          with tab1:
            st.markdown(result.reasoning)

          with tab2:
            st.markdown(result.math_explanation)

          with tab3:
            for note in result.pedagogical_notes:
              st.info(note)

          if show_technical:
            with st.expander("Raw Vision Description"):
              st.text(result.vision_description)


def render_vlm_chat(file_path:str, api_key:str):
  st.subheader(" Ask About Any Figure")

  if "vlm_figures" not in st.session_state or not st.session_state.vlm_figures:
    st.info("Scan the PDF for figures first using the Vision Analysis panel.")
    return

  from backend.math_wizard.vision import VisionDescriber
  from backend.math_wizard.vlm_reasoner import VLMReasoner

  if "vlm_chat_history" not in st.session_state:
    st.session_state.vlm_chat_history = []

  for msg in st.session_state.vlm_chat_history:
    with st.chat_message(msg["role"]):
      st.write(msg["content"])

  if prompt:= st.chat_input("Ask about a figure..."):
    st.session_state.vlm_chat_history.append({"role":"user", "content":prompt})

    with st.chat_message("user"):
      st.write(prompt)

    with st.chat_message("assistant"):
      with st.spinner("Analyzing..."):
        try:
          vision = VisionDescriber()
          reasoner = VLMReasoner(vision)

          combined_desc = ""
          for fig in st.session_state.vlm_figures[:3]:
            desc = vision.describe_math_figure(fig.image_bytes, fig.caption)
            combined_desc += f"\nFigure on page {fig.page_number}:{desc}\n"

          response = reasoner.answer_figure_question(
            image_bytes=st.session_state.vlm_figures[0].image_bytes,
            question=prompt,
            vision_description=combined_desc,
            api_key=api_key
          )

          st.write(response)
          st.session_state.vlm_chat_history.append({"role":"assistant", "content":response})

        except Exception as e:
          error_msg = f"Analysis failed:{e}"
          st.error(error_msg)
          st.session_state.vlm_chat_history.append({"role":"assistant", "content":error_msg})
