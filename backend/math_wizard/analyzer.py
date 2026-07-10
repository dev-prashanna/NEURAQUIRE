import fitz
import re
import uuid
import logging
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class BoundingBox:
    x1: float
    y1: float
    x2: float
    y2: float
    page_width: float = 0.0
    page_height: float = 0.0


@dataclass
class MathFormula:
    id: str
    latex: str
    page: int
    bbox: tuple[float, float, float, float]
    context: str
    confidence: float
    importance: str = "supporting"
    related_formulas: list[str] = field(default_factory=list)


@dataclass
class MathContext:
    document_id: str
    formulas: list[MathFormula]
    topics: list[str]
    difficulty_level: str = "grade_12"


class MathAnalyzer:
    MATH_PATTERNS = [
        r'\\(?:int|sum|prod|lim|frac|sqrt|pow|cdot|times)',
        r'\\(?:alpha|beta|gamma|delta|theta|pi|sigma|omega|lambda|mu)',
        r'\\(?:sin|cos|tan|sec|csc|cot|arcsin|arccos|arctan)',
        r'\\(?:log|ln|exp|det|dim|ker|hom|lim|sup|inf|max|min)',
        r'[∫∑∏∂∇√∞±≤≥≠≈∈∉⊂⊃∪∩∧∨¬→←↔⇒⇐⇔]',
        r'\^[{(].*[})]|_{[{].*[})]',
        r'\\(?:begin|end)\{[a-z]+\}',
        r'\\(?:frac|dfrac|tfrac|cfrac)\{',
        r'\\(?:overline|underline|hat|bar|vec|dot|ddot)\{',
        r'\\(?:left|right)[(\[\{|)\]\}]',
        r'(?:\\frac\{[^}]+\}\{[^}]+\})',
        r'(?:[a-zA-Z]\s*[=<>≤≥≠]\s*[\d\w])',
        r'(?:\d+\s*[+\-*/÷×]\s*\d+)',
    ]

    COMPOUND_PATTERNS = [
        r'(?:\\int|\\iint|\\iiint|\\oint)(?:_\{[^}]*\})?(?:\^\{[^}]*\})?',
        r'(?:\\sum|\\prod|\\coprod)(?:_\{[^}]*\})?(?:\^\{[^}]*\})?',
        r'(?:\\lim)(?:_\{[^}]*\})?',
    ]

    def __init__(self):
        self._compiled_patterns = [re.compile(p, re.IGNORECASE) for p in self.MATH_PATTERNS]
        self._compiled_compound = [re.compile(p) for p in self.COMPOUND_PATTERNS]

    def analyze_document(self, pdf_path: str) -> MathContext:
        logger.info(f"Analyzing document for math content: {pdf_path}")
        formulas = self.extract_formulas(pdf_path)
        topics = self._identify_topics(formulas)
        logger.info(f"Found {len(formulas)} formulas, topics: {topics}")

        return MathContext(
            document_id=str(uuid.uuid4()),
            formulas=formulas,
            topics=topics,
            difficulty_level="grade_12"
        )

    def extract_formulas(self, pdf_path: str) -> list[MathFormula]:
        formulas = []
        doc = fitz.open(pdf_path)

        for page_num in range(len(doc)):
            page = doc[page_num]
            text_dict = page.get_text("dict")
            page_width = page.rect.width
            page_height = page.rect.height

            for block in text_dict["blocks"]:
                if "lines" not in block:
                    continue

                for line in block["lines"]:
                    line_text = "".join(span["text"] for span in line["spans"])

                    if self._is_math_content(line_text):
                        merged_bbox = self._merge_span_bboxes(line["spans"])
                        formula = self._create_formula(
                            line_text, page_num + 1, merged_bbox,
                            page_width, page_height
                        )
                        if formula:
                            formulas.append(formula)

        doc.close()
        return formulas

    def _is_math_content(self, text: str) -> bool:
        if not text or len(text.strip()) < 2:
            return False

        for pattern in self._compiled_compound:
            if pattern.search(text):
                return True

        match_count = 0
        for pattern in self._compiled_patterns:
            if pattern.search(text):
                match_count += 1

        return match_count >= 2

    def _merge_span_bboxes(self, spans: list[dict]) -> tuple[float, float, float, float]:
        if not spans:
            return (0, 0, 0, 0)

        x1 = min(s["bbox"][0] for s in spans)
        y1 = min(s["bbox"][1] for s in spans)
        x2 = max(s["bbox"][2] for s in spans)
        y2 = max(s["bbox"][3] for s in spans)

        return (x1, y1, x2, y2)

    def _create_formula(
        self, text: str, page: int, bbox: tuple,
        page_width: float, page_height: float
    ) -> MathFormula | None:
        latex = self._text_to_latex(text)
        if not latex:
            return None

        context = self._get_context(text)
        confidence = self._calculate_confidence(text)
        importance = self._assess_importance(text, confidence)

        return MathFormula(
            id=str(uuid.uuid4()),
            latex=latex,
            page=page,
            bbox=bbox,
            context=context,
            confidence=confidence,
            importance=importance
        )

    def _text_to_latex(self, text: str) -> str:
        text = text.strip()

        replacements = {
            '∫': r'\int ', '∑': r'\sum ', '∏': r'\prod ',
            '∂': r'\partial ', '∇': r'\nabla ', '√': r'\sqrt{}',
            '∞': r'\infty ', '±': r'\pm ', '≤': r'\leq ',
            '≥': r'\geq ', '≠': r'\neq ', '≈': r'\approx ',
            '∈': r'\in ', '∉': r'\notin ', '⊂': r'\subset ',
            '⊃': r'\supset ', '∪': r'\cup ', '∩': r'\cap ',
            '×': r'\times ', '÷': r'\div ', '·': r'\cdot ',
            'α': r'\alpha ', 'β': r'\beta ', 'γ': r'\gamma ',
            'δ': r'\delta ', 'θ': r'\theta ', 'π': r'\pi ',
            'σ': r'\sigma ', 'ω': r'\omega ', 'λ': r'\lambda ',
            'μ': r'\mu ',
        }

        for char, latex in replacements.items():
            text = text.replace(char, latex)

        text = re.sub(r'(\w)\^(\w)', r'\1^{\2}', text)
        text = re.sub(r'(\w)_(\w)', r'\1_{\2}', text)

        return text

    def _get_context(self, text: str) -> str:
        return text[:200]

    def _calculate_confidence(self, text: str) -> float:
        score = 0.0

        for pattern in self._compiled_patterns:
            if pattern.search(text):
                score += 0.15

        if any(cmd in text for cmd in ['\\frac', '\\sqrt', '\\int', '\\sum']):
            score += 0.2

        return min(score, 1.0)

    def _assess_importance(self, text: str, confidence: float) -> str:
        if confidence > 0.6 or any(cmd in text for cmd in ['\\int', '\\sum', '\\prod']):
            return "key"
        elif confidence > 0.3:
            return "supporting"
        return "reference"

    def _identify_topics(self, formulas: list[MathFormula]) -> list[str]:
        topics = set()
        all_text = " ".join(f.latex + " " + f.context for f in formulas).lower()

        topic_keywords = {
            "calculus": ["integral", "derivative", "limit", "differential", "int", "partial"],
            "algebra": ["equation", "polynomial", "matrix", "vector", "linear"],
            "trigonometry": ["sin", "cos", "tan", "angle", "trigonometric"],
            "statistics": ["mean", "variance", "probability", "distribution", "sigma"],
            "linear_algebra": ["matrix", "determinant", "eigenvalue", "eigenvector"],
            "geometry": ["area", "volume", "perimeter", "angle", "triangle"],
            "number_theory": ["prime", "divisible", "modular", "gcd"],
            "set_theory": ["union", "intersection", "subset", "complement"],
        }

        for topic, keywords in topic_keywords.items():
            if any(kw in all_text for kw in keywords):
                topics.add(topic)

        return list(topics) if topics else ["general_math"]

    def find_formula_by_id(self, formulas: list[MathFormula], formula_id: str) -> MathFormula | None:
        for f in formulas:
            if f.id == formula_id:
                return f
        return None

    def get_formulas_on_page(self, formulas: list[MathFormula], page_num: int) -> list[MathFormula]:
        return [f for f in formulas if f.page == page_num]
