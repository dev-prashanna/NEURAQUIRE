import os
import uuid
import hashlib
import re
import time
import logging
from collections import defaultdict
from pathlib import Path
from backend.config import settings

logger = logging.getLogger(__name__)

MAX_UPLOAD_SIZE_MB = settings.MAX_UPLOAD_SIZE_MB
ALLOWED_MIME_TYPES = {"application/pdf"}
ALLOWED_EXTENSIONS = settings.ALLOWED_EXTENSIONS
MAX_QUESTION_LENGTH = settings.MAX_QUESTION_LENGTH
FILE_TTL_SECONDS = settings.FILE_TTL_SECONDS


class RateLimiter:
    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)

    def _clean_old(self, key: str, now: float) -> None:
        cutoff = now - self.window_seconds
        self._requests[key] = [
            t for t in self._requests[key] if t > cutoff
        ]

    def allow(self, key: str = "default") -> tuple[bool, float]:
        now = time.time()
        self._clean_old(key, now)

        if len(self._requests[key]) >= self.max_requests:
            oldest = self._requests[key][0]
            retry_after = self.window_seconds - (now - oldest)
            logger.warning(f"Rate limit exceeded for user={key}, retry_after={retry_after:.0f}s")
            return False, retry_after

        self._requests[key].append(now)
        return True, 0.0

    def remaining(self, key: str = "default") -> int:
        now = time.time()
        self._clean_old(key, now)
        return max(0, self.max_requests - len(self._requests[key]))


class CostTracker:
    def __init__(self):
        self._costs: dict[str, float] = defaultdict(float)

    def record(self, key: str, tokens_used: int) -> float:
        cost = (tokens_used / 1000) * settings.LLM_PRICE_PER_1K_TOKENS
        self._costs[key] += cost
        logger.info(f"LLM cost recorded: user={key} tokens={tokens_used} cost=${cost:.6f} total=${self._costs[key]:.4f}")
        return cost

    def total(self, key: str) -> float:
        return self._costs[key]


llm_rate_limiter = RateLimiter(
    max_requests=settings.RATE_LIMIT_MAX_REQUESTS,
    window_seconds=settings.RATE_LIMIT_WINDOW_SECONDS
)
llm_cost_tracker = CostTracker()


def sanitize_filename(filename: str) -> str:
    name = Path(filename).name
    name = "".join(c for c in name if c.isalnum() or c in "._-")
    if not name or name.startswith("."):
        name = "unnamed.pdf"
    return name


def validate_file(filename: str, file_size: int) -> tuple[bool, str]:
    name = Path(filename).name
    ext = Path(name).suffix.lower()

    if ext not in ALLOWED_EXTENSIONS:
        logger.warning(f"Invalid file extension rejected: {ext} (file={filename})")
        return False, f"Invalid file extension: {ext}. Only PDFs are allowed."

    if file_size > MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        logger.warning(f"File too large rejected: {file_size / 1024 / 1024:.1f}MB (file={filename})")
        return False, f"File too large. Maximum size is {MAX_UPLOAD_SIZE_MB}MB."

    logger.info(f"File validated: {filename} ({file_size / 1024:.0f}KB)")
    return True, ""


def generate_safe_filepath(upload_dir: str, original_filename: str) -> str:
    safe_name = sanitize_filename(original_filename)
    unique_id = uuid.uuid4().hex[:12]
    safe_name = f"{unique_id}_{safe_name}"
    file_path = os.path.join(upload_dir, safe_name)

    real_upload = os.path.realpath(upload_dir)
    real_file = os.path.realpath(file_path)

    if not real_file.startswith(real_upload):
        logger.error(f"Path traversal detected: {file_path}")
        raise ValueError(f"Path traversal detected: {file_path}")

    logger.info(f"Safe filepath generated: {safe_name}")
    return file_path


def file_hash(file_path: str) -> str:
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions|prompts|rules|context)",
    r"forget\s+(everything|all|previous|prior)",
    r"you\s+are\s+now\s+(a|an)\s+",
    r"act\s+as\s+(if|a|an)\s+",
    r"new\s+instructions?\s*:",
    r"system\s*prompt\s*:",
    r"output\s+(the|your)\s+(system|full)\s+(prompt|instructions?)",
    r"repeat\s+(the|your)\s+(system|full)\s+(prompt|instructions?)",
    r"disregard\s+(all|any|previous)",
    r"override\s+(all|any|previous|your)",
    r"reveal\s+(your|the)\s+(instructions?|prompt|rules?)",
    r"what\s+(are|is)\s+your\s+(instructions?|system\s+prompt|rules?)",
    r"print\s+(your|the)\s+(instructions?|prompt|rules?)",
    r"developer\s+mode",
    r"jailbreak",
    r"DAN\s+mode",
    r"do\s+anything\s+now",
    r"bypass\s+(all|any|your)\s+(filters?|rules?|restrictions?|safety)",
    r"no\s+restrictions?\s+mode",
]

INJECTION_COMPILED = [re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS]


class PromptInjectionDetected(Exception):
    pass


def sanitize_question(question: str) -> str:
    if len(question) > MAX_QUESTION_LENGTH:
        logger.warning(f"Question too long rejected: {len(question)} chars")
        raise PromptInjectionDetected("Question too long. Maximum 500 characters.")

    for pattern in INJECTION_COMPILED:
        if pattern.search(question):
            logger.warning(f"Prompt injection detected: {question[:100]}")
            raise PromptInjectionDetected(
                "Your question contains blocked patterns. "
                "Please ask questions directly about the paper content."
            )

    return question


def sanitize_for_prompt(text: str) -> str:
    text = text.replace("\\", "\\\\")
    text = text.replace("{", "\\{")
    text = text.replace("}", "\\}")
    return text


def cleanup_old_files(directory: str, ttl_seconds: int = FILE_TTL_SECONDS) -> int:
    if not os.path.exists(directory):
        return 0

    now = time.time()
    deleted = 0

    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        if not os.path.isfile(file_path):
            continue

        file_age = now - os.path.getmtime(file_path)
        if file_age > ttl_seconds:
            try:
                os.remove(file_path)
                deleted += 1
                logger.info(f"Deleted expired file: {filename} (age: {file_age:.0f}s)")
            except OSError as e:
                logger.error(f"Failed to delete {file_path}: {e}")

    return deleted


def delete_file(file_path: str) -> bool:
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Deleted file: {file_path}")
            return True
        return False
    except OSError as e:
        logger.error(f"Failed to delete {file_path}: {e}")
        return False


def get_upload_dir_size(directory: str) -> int:
    if not os.path.exists(directory):
        return 0

    total_size = 0
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        if os.path.isfile(file_path):
            total_size += os.path.getsize(file_path)

    return total_size
