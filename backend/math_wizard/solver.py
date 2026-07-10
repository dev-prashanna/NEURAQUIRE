import logging
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class DifficultyLevel(Enum):
    GRADE_12 = "grade_12"
    UNDERGRAD = "undergrad"
    GRADUATE = "graduate"


@dataclass
class SolutionStep:
    step_number: int
    title: str
    explanation: str
    math_content: str
    code_snippet: str | None = None
    annotation_ids: list[str] = field(default_factory=list)
    pedagogical_note: str = ""
    confidence: float = 0.9
    highlight_regions: list[dict] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class MathSolver:
    def __init__(self, llm_client, math_analyzer=None):
        self.llm = llm_client
        self.analyzer = math_analyzer
        self.difficulty = DifficultyLevel.GRADE_12

    def solve_problem(
        self,
        problem: str,
        context=None,
        difficulty: DifficultyLevel = DifficultyLevel.GRADE_12,
        history: list = None
    ) -> list[SolutionStep]:
        self.difficulty = difficulty

        prompt = self._build_solving_prompt(problem, context, history)
        response = self._call_llm(prompt)

        steps = self._parse_steps(response)

        for step in steps:
            if not step.pedagogical_note:
                step.pedagogical_note = self._generate_teaching_note(step)

        logger.info(f"Generated {len(steps)} solution steps")
        return steps

    def _build_solving_prompt(self, problem: str, context=None, history: list = None) -> str:
        context_section = ""
        if context and hasattr(context, 'formulas'):
            formulas_text = "\n".join(
                f"- {f.latex} (importance: {f.importance})"
                for f in context.formulas[:10]
            )
            context_section = f"\nRELEVANT FORMULAS:\n{formulas_text}\n"

        history_section = ""
        if history:
            history_lines = []
            for msg in history[-6:]:
                prefix = "User" if msg.get("role") == "user" else "Assistant"
                history_lines.append(f"{prefix}: {msg.get('content', '')[:200]}")
            history_section = "\nCONVERSATION HISTORY:\n" + "\n".join(history_lines) + "\n"

        difficulty_desc = {
            DifficultyLevel.GRADE_12: "a Grade 12 student (17-18 years old)",
            DifficultyLevel.UNDERGRAD: "an undergraduate student",
            DifficultyLevel.GRADUATE: "a graduate student"
        }

        return f"""You are Math Wizard, an expert math tutor. Solve this problem step-by-step for {difficulty_desc[self.difficulty]}.

PROBLEM:
{problem}
{context_section}{history_section}
INSTRUCTIONS:
1. Break this into clear, logical steps
2. For EACH step, provide:
   - Title: Short descriptive title
   - Explanation: What we're doing and WHY (teaching style)
   - Math: The LaTeX formula for this step (wrapped in $$)
   - Code: Optional Python code to verify (or "None")
   - Teaching: Everyday intuition (1-2 sentences)
   - Regions: Page number and approximate bbox to highlight [page, x1, y1, x2, y2]

3. Show ALL intermediate work - never skip steps
4. Use everyday analogies for teaching notes
5. Verify final answers when possible

OUTPUT FORMAT (strict):
STEP 1: [Title]
EXPLANATION: [What and why]
MATH: $$[LaTeX formula]$$
CODE: [Python code or None]
TEACHING: [Grade 12 intuition]
REGIONS: [page=X, bbox=[x1, y1, x2, y2]]

STEP 2: [Title]
EXPLANATION: [...]
MATH: $$[...]$$
CODE: [...]
TEACHING: [...]
REGIONS: [...]

FINAL ANSWER:
$$[Boxed final answer with \\boxed{{}}]$$
"""

    def _call_llm(self, prompt: str) -> str:
        try:
            from openai import OpenAI
            from backend.config import settings

            client = OpenAI(
                api_key=getattr(self, '_api_key', ''),
                base_url=settings.LLM_BASE_URL
            )

            response = client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=4096,
                temperature=0.3
            )

            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise

    def _parse_steps(self, response: str) -> list[SolutionStep]:
        steps = []
        step_pattern = r'STEP\s+(\d+)\s*:\s*(.+?)(?=STEP\s+\d+|FINAL\s+ANSWER|$)'
        step_matches = list(__import__('re').finditer(step_pattern, response, __import__('re').DOTALL))

        for match in step_matches:
            step_num = int(match.group(1))
            step_content = match.group(2)

            step = SolutionStep(
                step_number=step_num,
                title=self._extract_field(step_content, 'TITLE') or f"Step {step_num}",
                explanation=self._extract_field(step_content, 'EXPLANATION') or "",
                math_content=self._extract_math(step_content),
                code_snippet=self._extract_code(step_content),
                pedagogical_note=self._extract_field(step_content, 'TEACHING') or "",
                highlight_regions=self._extract_regions(step_content)
            )

            steps.append(step)

        if not steps:
            steps = self._fallback_parse(response)

        return steps

    def _extract_field(self, content: str, field_name: str) -> str | None:
        import re
        pattern = rf'{field_name}\s*:\s*(.+?)(?=EXPLANATION|MATH|CODE|TEACHING|REGIONS|STEP\s+\d+|$)'
        match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()
        return None

    def _extract_math(self, content: str) -> str:
        import re
        math_match = re.search(r'\$\$(.+?)\$\$', content, re.DOTALL)
        if math_match:
            return math_match.group(1).strip()

        math_match = re.search(r'MATH\s*:\s*(.+?)(?=CODE|TEACHING|REGIONS|STEP\s+\d+|$)', content, re.IGNORECASE | re.DOTALL)
        if math_match:
            text = math_match.group(1).strip()
            text = re.sub(r'^\$', '', text)
            text = re.sub(r'\$$', '', text)
            return text

        return ""

    def _extract_code(self, content: str) -> str | None:
        import re
        code_match = re.search(r'CODE\s*:\s*(.+?)(?=TEACHING|REGIONS|STEP\s+\d+|$)', content, re.IGNORECASE | re.DOTALL)
        if code_match:
            code = code_match.group(1).strip()
            if code.lower() in ('none', 'n/a', ''):
                return None
            return code
        return None

    def _extract_regions(self, content: str) -> list[dict]:
        import re
        regions = []
        region_pattern = r'page\s*=\s*(\d+).*?bbox\s*=\s*\[(\d+\.?\d*)\s*,\s*(\d+\.?\d*)\s*,\s*(\d+\.?\d*)\s*,\s*(\d+\.?\d*)\]'

        for match in re.finditer(region_pattern, content, re.IGNORECASE):
            regions.append({
                "page": int(match.group(1)),
                "bbox": [float(match.group(2)), float(match.group(3)),
                        float(match.group(4)), float(match.group(5))]
            })

        return regions

    def _fallback_parse(self, response: str) -> list[SolutionStep]:
        import re
        paragraphs = response.split('\n\n')
        steps = []

        for i, para in enumerate(paragraphs):
            para = para.strip()
            if not para or len(para) < 20:
                continue

            has_math = '$$' in para or any(sym in para for sym in ['∫', '∑', '√', '='])
            if has_math or i < 3:
                math_content = ""
                math_match = re.search(r'\$\$(.+?)\$\$', para, re.DOTALL)
                if math_match:
                    math_content = math_match.group(1)

                steps.append(SolutionStep(
                    step_number=len(steps) + 1,
                    title=f"Step {len(steps) + 1}",
                    explanation=para[:500],
                    math_content=math_content
                ))

        return steps

    def _generate_teaching_note(self, step: SolutionStep) -> str:
        if step.pedagogical_note:
            return step.pedagogical_note

        prompt = f"""Explain this math step to a Grade 12 student using an everyday analogy.
Step: {step.title}
Math: {step.math_content}

Keep it under 2 sentences. Be encouraging."""

        try:
            return self._call_llm(prompt)
        except Exception:
            return f"This step involves {step.title.lower()}. Think of it as building blocks - each step makes the problem simpler!"

    def generate_practice_variations(
        self,
        original_problem: str,
        steps: list[SolutionStep],
        count: int = 3
    ) -> list[str]:
        prompt = f"""Generate {count} practice problems similar to:
{original_problem}

Use the same mathematical concepts but with different numbers or contexts.
Make them progressively harder.

OUTPUT: One problem per line, prefixed with number."""

        try:
            response = self._call_llm(prompt)
            problems = []
            for line in response.strip().split('\n'):
                line = line.strip()
                if line and line[0].isdigit():
                    problem = __import__('re').sub(r'^\d+[\.\)]\s*', '', line)
                    problems.append(problem)
            return problems[:count]
        except Exception:
            return []

    def explain_concept(self, concept: str, context=None) -> str:
        prompt = f"""Explain the mathematical concept of "{concept}" to a Grade 12 student.

Use everyday analogies. Be encouraging. Include:
1. What it means in simple terms
2. A real-world example
3. Why it's useful

Keep it under 3 paragraphs."""

        return self._call_llm(prompt)

    def verify_answer(self, problem: str, answer: str, steps: list[SolutionStep]) -> dict:
        steps_text = "\n".join(
            f"Step {s.step_number}: {s.title} - {s.math_content}"
            for s in steps
        )

        prompt = f"""Verify this math solution:

PROBLEM: {problem}
FINAL ANSWER: {answer}

STEPS:
{steps_text}

Check:
1. Is the final answer correct?
2. Are all steps logically sound?
3. Any calculation errors?

OUTPUT format:
CORRECT: [Yes/No]
CONFIDENCE: [0.0-1.0]
ISSUES: [List any issues or "None"]
"""

        try:
            response = self._call_llm(prompt)
            return {
                "correct": "Yes" in response.split("CORRECT:")[-1].split("\n")[0],
                "response": response
            }
        except Exception:
            return {"correct": None, "response": "Verification failed"}
