import streamlit as st
import base64
import fitz
import os
import logging

logger = logging.getLogger(__name__)


def render_pdf_canvas(file_path:str, annotations:list = None, current_page:int = 0):
  if not os.path.exists(file_path):
    st.error("PDF file not found")
    return

  doc = fitz.open(file_path)
  total_pages = len(doc)

  if "pdf_current_page" not in st.session_state:
    st.session_state.pdf_current_page = current_page

  col1, col2, col3, col4 = st.columns([1, 2, 1, 1])
  with col1:
    if st.button("◀", key="prev_page"):
      st.session_state.pdf_current_page = max(0, st.session_state.pdf_current_page - 1)
  with col2:
    page_num = st.slider(
      "Page",
      1,
      total_pages,
      st.session_state.pdf_current_page + 1,
      key="page_slider"
    )
    st.session_state.pdf_current_page = page_num - 1
  with col3:
    if st.button("▶", key="next_page"):
      st.session_state.pdf_current_page = min(
        total_pages - 1,
        st.session_state.pdf_current_page + 1
      )
  with col4:
    st.caption(f"of {total_pages}")

  page = doc[st.session_state.pdf_current_page]
  pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
  img_data = pix.tobytes("png")
  img_base64 = base64.b64encode(img_data).decode()

  page_annotations = []
  if annotations:
    page_annotations = [
      a for a in annotations
      if (a.page_number - 1) == st.session_state.pdf_current_page
    ]

  annotations_html = _build_annotations_html(page_annotations, page.rect.width, page.rect.height)

  pdf_html = f"""
  <!DOCTYPE html>
  <html>
  <head>
    <style>
      .pdf-container {{
        position:relative;
        display:inline-block;
        width:100%;
        overflow:auto;
      }}
      .pdf-image {{
        width:100%;
        height:auto;
      }}
      .annotation {{
        position:absolute;
        cursor:pointer;
        border-radius:3px;
        transition:all 0.2s ease;
        z-index:10;
      }}
      .annotation:hover {{
        transform:scale(1.02);
        box-shadow:0 4px 12px rgba(0,0,0,0.3);
        z-index:20;
      }}
      .highlight {{
        opacity:0.4;
      }}
      .highlight:hover {{
        opacity:0.7;
      }}
      .marker {{
        border:3px solid;
        background:transparent;
      }}
      .note {{
        background:#FFFACD;
        border:2px solid #FFD700;
        padding:4px 8px;
        font-size:11px;
        max-width:200px;
        box-shadow:2px 2px 5px rgba(0,0,0,0.2);
      }}
      .underline {{
        border-bottom:3px solid;
        height:4px;
      }}
      .text-box {{
        background:rgba(255,255,255,0.9);
        border:1px solid #ccc;
        padding:4px;
        font-size:10px;
      }}
      .step-indicator {{
        position:absolute;
        background:#4A90D9;
        color:white;
        padding:2px 6px;
        border-radius:10px;
        font-size:10px;
        font-weight:bold;
        z-index:30;
      }}
      .pulse {{
        animation:pulse 1s ease-in-out 3;
      }}
      @keyframes pulse {{
        0%, 100% {{ opacity:0.4; transform:scale(1); }}
        50% {{ opacity:0.8; transform:scale(1.05); }}
      }}
    </style>
  </head>
  <body>
    <div class="pdf-container">
      <img src="data:image/png;base64,{img_base64}" class="pdf-image">
      {annotations_html}
    </div>
  </body>
  </html>
  """

  st.iframe(pdf_html, height=650)

  doc.close()


def _build_annotations_html(annotations:list, page_width:float, page_height:float) -> str:
  html_parts = []

  for ann in annotations:
    x1, y1, x2, y2 = ann.coordinates
    width = x2 - x1
    height = y2 - y1

    style = f"left:{x1}%; top:{y1}%; width:{width}%; height:{height}%;"

    if ann.annotation_type == "highlight":
      style += f" background-color:{ann.color}40;"
      html_parts.append(
        f'<div class="annotation highlight pulse" style="{style}" '
        f'title="Highlight on page {ann.page_number}"></div>'
      )
    elif ann.annotation_type == "marker":
      style += f" border-color:{ann.color};"
      html_parts.append(
        f'<div class="annotation marker" style="{style}" '
        f'title="Formula:{ann.formula_reference or "marked"}"></div>'
      )
    elif ann.annotation_type == "note":
      html_parts.append(
        f'<div class="annotation note" style="left:{x1}%; top:{y1}%;">'
        f'{ann.content[:50]}</div>'
      )
    elif ann.annotation_type == "underline":
      style += f" border-color:{ann.color};"
      html_parts.append(
        f'<div class="annotation underline" style="{style}"></div>'
      )
    elif ann.annotation_type == "text_box":
      html_parts.append(
        f'<div class="annotation text-box" style="left:{x1}%; top:{y1}%;">'
        f'{ann.content[:30]}</div>'
      )

    if ann.step_reference:
      html_parts.append(
        f'<div class="step-indicator" style="left:{x1}%; top:calc({y1}% - 15px);">'
        f'S{ann.step_reference}</div>'
      )

  return "\n".join(html_parts)


def render_pdf_toolbar():
  col1, col2, col3, col4 = st.columns(4)

  with col1:
    if st.button(" Highlight", key="tool_highlight"):
      st.session_state.active_tool = "highlight"
  with col2:
    if st.button(" Note", key="tool_note"):
      st.session_state.active_tool = "note"
  with col3:
    if st.button(" Mark", key="tool_mark"):
      st.session_state.active_tool = "marker"
  with col4:
    if st.button("⬇ Export", key="tool_export"):
      st.session_state.export_requested = True

  active_tool = st.session_state.get("active_tool", None)
  if active_tool:
    st.info(f"Active tool:{active_tool.title()}. Click on the PDF to apply.")


def get_pdf_dimensions(file_path:str) -> tuple[float, float]:
  if not os.path.exists(file_path):
    return 612.0, 792.0

  doc = fitz.open(file_path)
  page = doc[0]
  width = page.rect.width
  height = page.rect.height
  doc.close()
  return width, height
