import base64
import logging
import io
import os
import re
import fitz
from dataclasses import dataclass, field
from PIL import Image

logger = logging.getLogger(__name__)


@dataclass
class FigureDescription:
    figure_id: str
    page_number: int
    image_bytes: bytes
    bbox: tuple[float, float, float, float]
    description: str = ""
    caption: str = ""
    figure_type: str = "unknown"
    labels: list[str] = field(default_factory=list)
    axes: list[str] = field(default_factory=list)


class VisionDescriber:
    def __init__(self):
        self._client = None

    def _get_client(self):
        if self._client is None:
            import google.generativeai as genai
            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key:
                raise ValueError(
                    "GOOGLE_API_KEY not set. Get one free at https://aistudio.google.com/apikey"
                )
            genai.configure(api_key=api_key)
            self._client = genai.GenerativeModel("gemini-1.5-flash")
        return self._client

    def describe_image(self, image_bytes: bytes, context: str = "", detail_level: str = "detailed") -> str:
        model = self._get_client()
        prompt = self._build_description_prompt(context, detail_level)
        response = model.generate_content([
            prompt,
            {"mime_type": "image/png", "data": image_bytes}
        ])
        return response.text

    def describe_math_figure(self, image_bytes: bytes, surrounding_text: str = "") -> str:
        model = self._get_client()
        prompt = f"""Analyze this mathematical figure from a research paper.

CONTEXT FROM DOCUMENT:
{surrounding_text[:500] if surrounding_text else "No surrounding context available."}

Describe:
1. What type of figure is this? (graph, chart, diagram, equation render, flowchart, etc.)
2. What mathematical concept does it illustrate?
3. What are the axes/labels (if applicable)?
4. What is the key takeaway or result shown?
5. What formulas or equations are visually represented?
6. Any notable data points, trends, or patterns?

Be specific about mathematical content. Use LaTeX notation where appropriate."""

        response = model.generate_content([
            prompt,
            {"mime_type": "image/png", "data": image_bytes}
        ])
        return response.text

    def extract_text_from_image(self, image_bytes: bytes) -> str:
        model = self._get_client()
        prompt = """Extract ALL text from this image.
Include:
- All printed text
- Handwritten text
- Labels, legends, annotations
- Axis labels and values
- Any mathematical expressions (use LaTeX notation)

Output the extracted text exactly as it appears, preserving structure."""

        response = model.generate_content([
            prompt,
            {"mime_type": "image/png", "data": image_bytes}
        ])
        return response.text

    def _build_description_prompt(self, context: str, detail_level: str) -> str:
        base = "Describe this image in detail."
        if context:
            base += f"\n\nContext: {context}"
        if detail_level == "detailed":
            base += "\n\nProvide a comprehensive description including all visible elements, text, labels, and mathematical content."
        elif detail_level == "concise":
            base += "\n\nProvide a brief summary of what this image shows."
        return base


class FigureExtractor:
    def __init__(self, pdf_path: str):
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        self.pdf_path = pdf_path
        self.doc = fitz.open(pdf_path)

    def extract_figures(self, min_width: int = 100, min_height: int = 100) -> list[FigureDescription]:
        figures = []

        for page_num in range(len(self.doc)):
            page = self.doc[page_num]
            images = page.get_images(full=True)

            for img_index, img in enumerate(images):
                xref = img[0]

                try:
                    base_image = self.doc.extract_image(xref)
                    img_bytes = base_image["image"]
                    img_width = base_image["width"]
                    img_height = base_image["height"]

                    if img_width < min_width or img_height < min_height:
                        continue

                    img_bbox = self._get_image_bbox(page, img)

                    if not img_bbox:
                        continue

                    pil_image = Image.open(io.BytesIO(img_bytes))
                    if pil_image.mode in ('RGBA', 'P'):
                        pil_image = pil_image.convert('RGB')

                    buf = io.BytesIO()
                    pil_image.save(buf, format='PNG')
                    png_bytes = buf.getvalue()

                    surrounding_text = self._get_surrounding_text(page, img_bbox)

                    figure = FigureDescription(
                        figure_id=f"fig_{page_num+1}_{img_index}",
                        page_number=page_num + 1,
                        image_bytes=png_bytes,
                        bbox=img_bbox,
                        caption=self._extract_caption(surrounding_text),
                        figure_type=self._classify_figure_type(surrounding_text),
                        labels=self._extract_labels(surrounding_text)
                    )

                    figures.append(figure)

                except Exception as e:
                    logger.warning(f"Failed to extract image {xref} from page {page_num+1}: {e}")
                    continue

        logger.info(f"Extracted {len(figures)} figures from PDF")
        return figures

    def _get_image_bbox(self, page, img) -> tuple[float, float, float, float] | None:
        try:
            img_rects = page.get_image_rects(img[0])
            if img_rects:
                rect = img_rects[0]
                return (rect.x0, rect.y0, rect.x1, rect.y1)
        except Exception:
            pass
        return None

    def _get_surrounding_text(self, page, bbox: tuple, radius: float = 100) -> str:
        text_dict = page.get_text("dict")
        surrounding = []

        cx = (bbox[0] + bbox[2]) / 2
        cy = (bbox[1] + bbox[3]) / 2

        for block in text_dict["blocks"]:
            if "lines" not in block:
                continue

            block_text = ""
            for line in block["lines"]:
                for span in line["spans"]:
                    block_text += span["text"] + " "

            if block_text.strip():
                block_bbox = block["bbox"]
                block_cx = (block_bbox[0] + block_bbox[2]) / 2
                block_cy = (block_bbox[1] + block_bbox[3]) / 2

                distance = ((block_cx - cx) ** 2 + (block_cy - cy) ** 2) ** 0.5

                if distance < radius:
                    surrounding.append(block_text.strip())

        return " ".join(surrounding[:5])

    def _extract_caption(self, text: str) -> str:
        caption_patterns = [
            r'Fig(?:ure|\.)\s*\d+[.:]\s*(.+?)(?=\n|$)',
            r'Figure\s+\d+[.:]\s*(.+?)(?=\n|$)',
        ]
        for pattern in caption_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()[:200]
        return ""

    def _classify_figure_type(self, text: str) -> str:
        text_lower = text.lower()

        if any(w in text_lower for w in ['graph', 'plot', 'curve', 'axis', 'x-axis', 'y-axis']):
            return "graph"
        elif any(w in text_lower for w in ['chart', 'bar', 'pie', 'histogram']):
            return "chart"
        elif any(w in text_lower for w in ['diagram', 'flowchart', 'block diagram']):
            return "diagram"
        elif any(w in text_lower for w in ['table', 'row', 'column']):
            return "table"
        elif any(w in text_lower for w in ['equation', 'formula', 'expression']):
            return "equation"
        else:
            return "figure"

    def _extract_labels(self, text: str) -> list[str]:
        labels = []
        label_patterns = [
            r'(?:label|legend|series)\s*[:=]\s*(.+?)(?=\n|$)',
            r'\(([a-zA-Z])\)\s*(.+?)(?=\n|$)',
        ]
        for pattern in label_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    labels.extend(match)
                else:
                    labels.append(match)
        return labels[:10]

    def close(self):
        if self.doc:
            self.doc.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
