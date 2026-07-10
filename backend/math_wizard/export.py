import fitz
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class AnnotatedPDFExporter:
    def __init__(self, pdf_path: str):
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        self.pdf_path = pdf_path
        self.doc = fitz.open(pdf_path)

    def add_solution_overlay(
        self,
        steps: list,
        position: str = "sidebar"
    ) -> None:
        for page_num in range(len(self.doc)):
            page = self.doc[page_num]
            page_steps = [
                s for s in steps
                if self._step_applies_to_page(s, page_num + 1)
            ]

            if page_steps:
                if position == "sidebar":
                    self._draw_solution_sidebar(page, page_steps)
                elif position == "bottom":
                    self._draw_solution_bottom(page, page_steps)

    def _step_applies_to_page(self, step, page_num: int) -> bool:
        if hasattr(step, 'highlight_regions'):
            for region in step.highlight_regions:
                if region.get("page") == page_num:
                    return True
        return page_num == 1

    def _draw_solution_sidebar(self, page, steps):
        rect = page.rect
        sidebar_width = 220
        margin = 10

        shape = page.new_shape()
        sidebar_rect = fitz.Rect(
            rect.width - sidebar_width - 5, 0,
            rect.width, rect.height
        )
        shape.draw_rect(sidebar_rect)
        shape.finish(fill=(0.96, 0.96, 0.96), color=(0.8, 0.8, 0.8))
        shape.commit()

        page.insert_text(
            fitz.Point(rect.width - sidebar_width + margin, 25),
            "Math Wizard Solution",
            fontsize=12,
            fontname="helv",
            color=(0.2, 0.2, 0.6)
        )

        y_pos = 50
        for step in steps:
            if y_pos > rect.height - 50:
                break

            step_text = f"Step {step.step_number}: {step.title}"
            page.insert_text(
                fitz.Point(rect.width - sidebar_width + margin, y_pos),
                step_text[:30],
                fontsize=9,
                fontname="helv",
                color=(0.1, 0.1, 0.1)
            )
            y_pos += 14

            if step.math_content:
                math_text = step.math_content[:50]
                page.insert_text(
                    fitz.Point(rect.width - sidebar_width + margin + 5, y_pos),
                    math_text,
                    fontsize=8,
                    fontname="cour",
                    color=(0.3, 0.3, 0.6)
                )
                y_pos += 12

            explanation_lines = self._wrap_text(step.explanation, 28)
            for line in explanation_lines[:2]:
                if y_pos > rect.height - 30:
                    break
                page.insert_text(
                    fitz.Point(rect.width - sidebar_width + margin, y_pos),
                    line,
                    fontsize=7,
                    fontname="helv",
                    color=(0.4, 0.4, 0.4)
                )
                y_pos += 10

            y_pos += 8

    def _draw_solution_bottom(self, page, steps):
        rect = page.rect
        bottom_height = 200
        margin = 15

        shape = page.new_shape()
        bottom_rect = fitz.Rect(
            0, rect.height - bottom_height,
            rect.width, rect.height
        )
        shape.draw_rect(bottom_rect)
        shape.finish(fill=(0.96, 0.96, 0.96), color=(0.8, 0.8, 0.8))
        shape.commit()

        y_pos = rect.height - bottom_height + margin

        page.insert_text(
            fitz.Point(margin, y_pos),
            "Solution Steps:",
            fontsize=11,
            fontname="helv",
            color=(0.2, 0.2, 0.6)
        )
        y_pos += 18

        for step in steps:
            if y_pos > rect.height - margin:
                break

            step_text = f"{step.step_number}. {step.title}"
            page.insert_text(
                fitz.Point(margin, y_pos),
                step_text[:60],
                fontsize=9,
                fontname="helv",
                color=(0.1, 0.1, 0.1)
            )
            y_pos += 14

    def add_formula_glossary(self, formulas: list, page_num: int = -1) -> None:
        if page_num == -1:
            page = self.doc.new_page(width=612, height=792)
        else:
            page = self.doc[page_num - 1]

        y_pos = 50

        page.insert_text(
            fitz.Point(50, y_pos),
            "Formula Glossary",
            fontsize=18,
            fontname="helv",
            color=(0, 0, 0)
        )
        y_pos += 30

        page.draw_line(fitz.Point(50, y_pos), fitz.Point(562, y_pos))
        y_pos += 20

        for formula in formulas:
            if y_pos > 750:
                page = self.doc.new_page(width=612, height=792)
                y_pos = 50

            importance_color = {
                "key": (0.8, 0.1, 0.1),
                "supporting": (0.2, 0.2, 0.2),
                "reference": (0.5, 0.5, 0.5)
            }
            color = importance_color.get(formula.importance, (0.2, 0.2, 0.2))

            page.insert_text(
                fitz.Point(50, y_pos),
                f"• {formula.id[:8]}...",
                fontsize=9,
                fontname="helv",
                color=color
            )

            latex_text = formula.latex[:70]
            page.insert_text(
                fitz.Point(120, y_pos),
                latex_text,
                fontsize=9,
                fontname="cour",
                color=(0.2, 0.2, 0.5)
            )

            y_pos += 15

            if formula.context:
                context_text = formula.context[:80]
                page.insert_text(
                    fitz.Point(120, y_pos),
                    context_text,
                    fontsize=8,
                    fontname="helv",
                    color=(0.4, 0.4, 0.4)
                )
                y_pos += 15

            y_pos += 10

    def add_metadata_page(
        self,
        problem: str,
        steps: list,
        final_answer: str
    ) -> None:
        page = self.doc.new_page(width=612, height=792)
        y_pos = 50

        page.insert_text(
            fitz.Point(50, y_pos),
            "Math Wizard - Problem Solution",
            fontsize=16,
            fontname="helv",
            color=(0, 0, 0)
        )
        y_pos += 25

        page.insert_text(
            fitz.Point(50, y_pos),
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            fontsize=10,
            fontname="helv",
            color=(0.5, 0.5, 0.5)
        )
        y_pos += 30

        page.insert_text(
            fitz.Point(50, y_pos),
            "Problem:",
            fontsize=12,
            fontname="helv",
            color=(0.2, 0.2, 0.6)
        )
        y_pos += 15

        problem_lines = self._wrap_text(problem, 70)
        for line in problem_lines[:3]:
            page.insert_text(
                fitz.Point(60, y_pos),
                line,
                fontsize=10,
                fontname="helv",
                color=(0, 0, 0)
            )
            y_pos += 14
        y_pos += 15

        page.insert_text(
            fitz.Point(50, y_pos),
            "Solution Steps:",
            fontsize=12,
            fontname="helv",
            color=(0.2, 0.2, 0.6)
        )
        y_pos += 18

        for step in steps:
            if y_pos > 700:
                page = self.doc.new_page(width=612, height=792)
                y_pos = 50

            page.insert_text(
                fitz.Point(60, y_pos),
                f"Step {step.step_number}: {step.title}",
                fontsize=10,
                fontname="helv",
                color=(0.1, 0.1, 0.1)
            )
            y_pos += 14

            if step.math_content:
                page.insert_text(
                    fitz.Point(70, y_pos),
                    step.math_content[:60],
                    fontsize=9,
                    fontname="cour",
                    color=(0.2, 0.2, 0.5)
                )
                y_pos += 12

            y_pos += 8

        y_pos += 10
        page.insert_text(
            fitz.Point(50, y_pos),
            "Final Answer:",
            fontsize=12,
            fontname="helv",
            color=(0.2, 0.2, 0.6)
        )
        y_pos += 18

        page.insert_text(
            fitz.Point(60, y_pos),
            final_answer[:80],
            fontsize=11,
            fontname="cour",
            color=(0, 0.4, 0)
        )

    def export(self, output_path: str) -> str:
        self.doc.save(output_path)
        logger.info(f"Exported annotated PDF to: {output_path}")
        return output_path

    def _wrap_text(self, text: str, max_chars: int) -> list[str]:
        words = text.split()
        lines = []
        current_line = []

        for word in words:
            if len(" ".join(current_line + [word])) <= max_chars:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(" ".join(current_line))
                current_line = [word]

        if current_line:
            lines.append(" ".join(current_line))

        return lines

    def close(self) -> None:
        if self.doc:
            self.doc.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
