import fitz
import uuid
import os
import logging
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class Annotation:
    id: str
    page_number: int
    annotation_type: str
    color: str
    coordinates: tuple[float, float, float, float]
    content: str
    formula_reference: str | None = None
    step_reference: int | None = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: dict = field(default_factory=dict)


class PDFAnnotator:
    def __init__(self, pdf_path: str):
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        self.pdf_path = pdf_path
        self.doc = fitz.open(pdf_path)
        self.annotations: list[Annotation] = []
        self._render_cache: dict[int, bytes] = {}

    def highlight_region(
        self,
        page_num: int,
        bbox: tuple[float, float, float, float],
        color: str = "#FFFF00",
        opacity: float = 0.4
    ) -> Annotation:
        page = self.doc[page_num - 1]
        rect = fitz.Rect(bbox)

        highlight = page.add_highlight_annot(rect)
        color_rgb = self._hex_to_rgb(color)
        highlight.set_colors(stroke=color_rgb)
        highlight.set_opacity(opacity)
        highlight.update()

        self._invalidate_cache(page_num)

        annotation = Annotation(
            id=str(uuid.uuid4()),
            page_number=page_num,
            annotation_type="highlight",
            color=color,
            coordinates=bbox,
            content=""
        )
        self.annotations.append(annotation)
        logger.info(f"Added highlight on page {page_num}: {bbox}")
        return annotation

    def add_note(
        self,
        page_num: int,
        position: tuple[float, float],
        text: str,
        color: str = "#0000FF"
    ) -> Annotation:
        page = self.doc[page_num - 1]
        point = fitz.Point(position)

        note = page.add_text_annot(point, text)
        color_rgb = self._hex_to_rgb(color)
        note.set_colors(stroke=color_rgb)
        note.set_info(title="Math Wizard Note", content=text)
        note.update()

        self._invalidate_cache(page_num)

        annotation = Annotation(
            id=str(uuid.uuid4()),
            page_number=page_num,
            annotation_type="note",
            color=color,
            coordinates=(position[0], position[1], position[0] + 200, position[1] + 50),
            content=text
        )
        self.annotations.append(annotation)
        logger.info(f"Added note on page {page_num} at {position}")
        return annotation

    def mark_formula(
        self,
        page_num: int,
        bbox: tuple[float, float, float, float],
        formula_id: str,
        color: str = "#FF0000"
    ) -> Annotation:
        page = self.doc[page_num - 1]
        rect = fitz.Rect(bbox)

        shape = page.new_shape()
        shape.draw_rect(rect)
        color_rgb = self._hex_to_rgb(color)
        shape.finish(color=color_rgb, width=2)
        shape.commit()

        self._invalidate_cache(page_num)

        annotation = Annotation(
            id=formula_id,
            page_number=page_num,
            annotation_type="marker",
            color=color,
            coordinates=bbox,
            content="",
            formula_reference=formula_id
        )
        self.annotations.append(annotation)
        logger.info(f"Marked formula {formula_id} on page {page_num}")
        return annotation

    def add_underline(
        self,
        page_num: int,
        bbox: tuple[float, float, float, float],
        color: str = "#00FF00"
    ) -> Annotation:
        page = self.doc[page_num - 1]
        rect = fitz.Rect(bbox)

        underline = page.add_underline_annot(rect)
        color_rgb = self._hex_to_rgb(color)
        underline.set_colors(stroke=color_rgb)
        underline.update()

        self._invalidate_cache(page_num)

        annotation = Annotation(
            id=str(uuid.uuid4()),
            page_number=page_num,
            annotation_type="underline",
            color=color,
            coordinates=bbox,
            content=""
        )
        self.annotations.append(annotation)
        return annotation

    def add_text_box(
        self,
        page_num: int,
        bbox: tuple[float, float, float, float],
        text: str,
        fontsize: int = 10,
        color: str = "#000000"
    ) -> Annotation:
        page = self.doc[page_num - 1]
        rect = fitz.Rect(bbox)

        text_writer = fitz.TextWriter(page.rect)
        font = fitz.Font("helv")
        text_writer.append(fitz.Point(rect.x0, rect.y0 + fontsize), text, font=font, fontsize=fontsize)
        text_writer.write_text(page)

        self._invalidate_cache(page_num)

        annotation = Annotation(
            id=str(uuid.uuid4()),
            page_number=page_num,
            annotation_type="text_box",
            color=color,
            coordinates=bbox,
            content=text
        )
        self.annotations.append(annotation)
        return annotation

    def mark_formulas(
        self,
        formulas: list,
        marker_color: str = "#FF0000"
    ) -> list[Annotation]:
        annotations = []
        for formula in formulas:
            bbox = formula.bbox if hasattr(formula, 'bbox') else formula
            page_num = formula.page if hasattr(formula, 'page') else 1
            formula_id = formula.id if hasattr(formula, 'id') else str(uuid.uuid4())

            ann = self.mark_formula(page_num, bbox, formula_id, marker_color)
            annotations.append(ann)

        return annotations

    def highlight_step_regions(
        self,
        step_number: int,
        regions: list[dict],
        color: str | None = None
    ) -> list[Annotation]:
        if color is None:
            step_colors = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7", "#DDA0DD", "#98D8C8"]
            color = step_colors[(step_number - 1) % len(step_colors)]

        annotations = []
        for region in regions:
            page_num = region.get("page", 1)
            bbox = tuple(region.get("bbox", (0, 0, 100, 20)))

            ann = self.highlight_region(page_num, bbox, color, opacity=0.5)
            ann.step_reference = step_number
            annotations.append(ann)

        return annotations

    def pulse_highlight(self, annotation_ids: list[str]) -> None:
        for ann in self.annotations:
            if ann.id in annotation_ids and ann.annotation_type == "highlight":
                logger.info(f"Pulsing highlight {ann.id}")

    def get_annotations_on_page(self, page_num: int) -> list[Annotation]:
        return [a for a in self.annotations if a.page_number == page_num]

    def get_all_annotations(self) -> list[Annotation]:
        return self.annotations.copy()

    def export_annotated(self, output_path: str) -> str:
        self.doc.save(output_path)
        logger.info(f"Exported annotated PDF to: {output_path}")
        return output_path

    def render_page_as_image(self, page_num: int, dpi: int = 150) -> bytes:
        if page_num in self._render_cache:
            return self._render_cache[page_num]

        page = self.doc[page_num - 1]
        mat = fitz.Matrix(dpi / 72, dpi / 72)
        pix = page.get_pixmap(matrix=mat)
        img_bytes = pix.tobytes("png")

        self._render_cache[page_num] = img_bytes
        return img_bytes

    def render_page_with_annotations(self, page_num: int, dpi: int = 150) -> bytes:
        return self.render_page_as_image(page_num, dpi)

    def _invalidate_cache(self, page_num: int) -> None:
        self._render_cache.pop(page_num, None)

    def _hex_to_rgb(self, hex_color: str) -> tuple[float, float, float]:
        hex_color = hex_color.lstrip('#')
        r = int(hex_color[0:2], 16) / 255.0
        g = int(hex_color[2:4], 16) / 255.0
        b = int(hex_color[4:6], 16) / 255.0
        return (r, g, b)

    def close(self) -> None:
        if self.doc:
            self.doc.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
