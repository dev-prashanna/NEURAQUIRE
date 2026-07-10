import logging
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class Message:
    role: str
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    sources: list = field(default_factory=list)


class ConversationHistory:
    def __init__(self, max_turns: int = 10):
        self.max_turns = max_turns
        self.messages: list[Message] = []

    def add_user_message(self, content: str) -> None:
        self.messages.append(Message(role="user", content=content))
        self._trim()
        logger.info(f"Added user message: {content[:50]}...")

    def add_assistant_message(self, content: str, sources: list = None) -> None:
        self.messages.append(Message(role="assistant", content=content, sources=sources or []))
        self._trim()
        logger.info(f"Added assistant message: {content[:50]}...")

    def _trim(self) -> None:
        if len(self.messages) > self.max_turns * 2:
            self.messages = self.messages[-(self.max_turns * 2):]

    def get_context(self, include_last_n: int = 3) -> list[dict]:
        recent = self.messages[-(include_last_n * 2):] if include_last_n else []
        return [{"role": msg.role, "content": msg.content} for msg in recent]

    def get_all(self) -> list[Message]:
        return self.messages.copy()

    def clear(self) -> None:
        self.messages.clear()
        logger.info("Conversation history cleared")

    def __len__(self) -> int:
        return len(self.messages)

    def __bool__(self) -> bool:
        return bool(self.messages)
