import logging
from dataclasses import dataclass, field
from openai import OpenAI
from backend.config import settings

logger = logging.getLogger(__name__)


@dataclass
class VLMResult:
    figure_id: str
    vision_description: str
    reasoning: str
    math_explanation: str
    pedagogical_notes: list[str] = field(default_factory=list)


class VLMReasoner:
    def __init__(self, vision_describer):
        self.vision = vision_describer
        self._llm_client = None

    def _get_llm_client(self, api_key: str = None) -> OpenAI:
        if self._llm_client is None:
            self._llm_client = OpenAI(
                api_key=api_key or "",
                base_url=settings.LLM_BASE_URL
            )
        return self._llm_client

    def analyze_figure_with_reasoning(
        self,
        image_bytes: bytes,
        surrounding_text: str = "",
        user_question: str = "",
        api_key: str = "",
        difficulty: str = "grade_12"
    ) -> VLMResult:
        import uuid

        logger.info("Starting VLM analysis pipeline: Gemini -> MiMo")

        vision_description = self.vision.describe_math_figure(image_bytes, surrounding_text)
        logger.info(f"Gemini description: {vision_description[:100]}...")

        reasoning = self._reason_with_llm(
            vision_description=vision_description,
            surrounding_text=surrounding_text,
            user_question=user_question,
            api_key=api_key,
            difficulty=difficulty
        )

        math_explanation = self._explain_math_concepts(
            vision_description=vision_description,
            surrounding_text=surrounding_text,
            api_key=api_key,
            difficulty=difficulty
        )

        return VLMResult(
            figure_id=f"vlm_{uuid.uuid4().hex[:8]}",
            vision_description=vision_description,
            reasoning=reasoning,
            math_explanation=math_explanation,
            pedagogical_notes=self._generate_teaching_notes(vision_description, api_key)
        )

    def _reason_with_llm(
        self,
        vision_description: str,
        surrounding_text: str,
        user_question: str,
        api_key: str,
        difficulty: str
    ) -> str:
        client = self._get_llm_client(api_key)

        difficulty_map = {
            "grade_12": "a Grade 12 student",
            "undergrad": "an undergraduate student",
            "graduate": "a graduate student"
        }

        question_section = ""
        if user_question:
            question_section = f"\n\nSPECIFIC QUESTION FROM USER:\n{user_question}"

        prompt = f"""You are MiMo, an expert math tutor. You have received a description of a figure from a research paper.

FIGURE DESCRIPTION (from Vision AI):
{vision_description}

SURROUNDING TEXT FROM DOCUMENT:
{surrounding_text[:1000] if surrounding_text else "No surrounding text available."}
{question_section}
YOUR TASK:
Provide a comprehensive analysis of this figure for {difficulty_map.get(difficulty, 'a Grade 12 student')}:

1. **INTERPRETATION**: What does this figure show in simple terms?
2. **MATHEMATICAL SIGNIFICANCE**: What mathematical concepts are illustrated?
3. **KEY INSIGHTS**: What are the 2-3 most important things to understand?
4. **REAL-WORLD CONNECTION**: How does this relate to real applications?
5. **COMMON MISTAKES**: What do students often misunderstand about this?

Use LaTeX notation for any mathematical expressions.
Be encouraging and educational. Start from basics and build up.
"""

        response = client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2048,
            temperature=0.3
        )

        return response.choices[0].message.content

    def _explain_math_concepts(
        self,
        vision_description: str,
        surrounding_text: str,
        api_key: str,
        difficulty: str
    ) -> str:
        client = self._get_llm_client(api_key)

        prompt = f"""Based on this figure from a research paper, explain the underlying mathematical concepts.

FIGURE DESCRIPTION:
{vision_description}

SURROUNDING TEXT:
{surrounding_text[:500]}

For a Grade 12 student, explain:
1. What mathematical formulas or equations are represented visually?
2. How would you write these in LaTeX?
3. What is the step-by-step reasoning behind the mathematics shown?
4. Connect this to formulas the student might know (e.g., y = mx + b, Pythagorean theorem, etc.)

Use clear, step-by-step explanations. Use LaTeX for math.
"""

        response = client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1500,
            temperature=0.3
        )

        return response.choices[0].message.content

    def _generate_teaching_notes(self, vision_description: str, api_key: str) -> list[str]:
        client = self._get_llm_client(api_key)

        prompt = f"""Generate 3 short teaching tips for a Grade 12 student about this figure:

{vision_description[:500]}

OUTPUT FORMAT (one tip per line):
TIP: [teaching tip]
TIP: [teaching tip]
TIP: [teaching tip]
"""

        response = client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.5
        )

        tips = []
        for line in response.choices[0].message.content.split("\n"):
            line = line.strip()
            if line.upper().startswith("TIP:"):
                tips.append(line[4:].strip())

        return tips[:3]

    def answer_figure_question(
        self,
        image_bytes: bytes,
        question: str,
        vision_description: str = "",
        api_key: str = ""
    ) -> str:
        if not vision_description:
            vision_description = self.vision.describe_math_figure(image_bytes)

        client = self._get_llm_client(api_key)

        prompt = f"""Based on this figure and its description, answer the user's question.

FIGURE DESCRIPTION:
{vision_description}

USER QUESTION:
{question}

Provide a clear, educational answer. Use LaTeX for math. Be encouraging.
"""

        response = client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1024,
            temperature=0.3
        )

        return response.choices[0].message.content
