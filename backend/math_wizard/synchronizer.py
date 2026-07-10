import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable

logger = logging.getLogger(__name__)


@dataclass
class SyncEvent:
    event_type: str
    source: str
    data: dict
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class MathWizardSynchronizer:
    EVENT_TYPES = {
        "highlight_regions": "PDF",
        "add_note": "PDF",
        "mark_formula": "PDF",
        "scroll_to_step": "SOLUTION",
        "pulse_highlight": "PDF",
        "add_step": "SOLUTION",
        "update_chat": "CHAT",
        "clear_highlights": "PDF",
        "export_request": "SYSTEM"
    }

    def __init__(self):
        self.listeners: dict[str, list[Callable]] = {}
        self.event_history: list[SyncEvent] = []
        self._state: dict = {
            "current_step": None,
            "highlighted_regions": [],
            "active_annotations": [],
            "sync_enabled": True
        }

    def on(self, event_type: str, callback: Callable):
        if event_type not in self.listeners:
            self.listeners[event_type] = []
        self.listeners[event_type].append(callback)
        logger.debug(f"Registered listener for event: {event_type}")

    def off(self, event_type: str, callback: Callable):
        if event_type in self.listeners:
            self.listeners[event_type] = [
                cb for cb in self.listeners[event_type] if cb != callback
            ]

    def emit(self, event: SyncEvent):
        self.event_history.append(event)

        if not self._state["sync_enabled"]:
            logger.debug(f"Sync disabled, skipping event: {event.event_type}")
            return

        target = self.EVENT_TYPES.get(event.event_type, "UNKNOWN")
        logger.info(f"Sync event: {event.event_type} -> {target}")

        for callback in self.listeners.get(event.event_type, []):
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Error in sync callback for {event.event_type}: {e}")

    def sync_step_to_pdf(self, step, annotations: list = None):
        regions = []
        if hasattr(step, 'highlight_regions'):
            regions = step.highlight_regions
        elif annotations:
            regions = [
                {"page": a.page_number, "bbox": a.coordinates}
                for a in annotations
            ]

        event = SyncEvent(
            event_type="highlight_regions",
            source="solution",
            data={
                "step_number": step.step_number if hasattr(step, 'step_number') else 1,
                "regions": regions,
                "color": self._get_step_color(step.step_number if hasattr(step, 'step_number') else 1)
            }
        )
        self.emit(event)

        self._state["current_step"] = step.step_number if hasattr(step, 'step_number') else None

    def sync_annotation_to_solution(self, annotation):
        if hasattr(annotation, 'step_reference') and annotation.step_reference:
            event = SyncEvent(
                event_type="scroll_to_step",
                source="pdf",
                data={"step_number": annotation.step_reference}
            )
            self.emit(event)

    def sync_hover_effect(self, step):
        annotation_ids = []
        if hasattr(step, 'annotation_ids'):
            annotation_ids = step.annotation_ids

        event = SyncEvent(
            event_type="pulse_highlight",
            source="solution",
            data={"annotation_ids": annotation_ids}
        )
        self.emit(event)

    def sync_click_to_chat(self, annotation, message: str = ""):
        if not message:
            if annotation.annotation_type == "note":
                message = f"Note on page {annotation.page_number}: {annotation.content}"
            elif annotation.annotation_type == "marker":
                message = f"Formula marked on page {annotation.page_number}"
            else:
                message = f"Annotation on page {annotation.page_number}"

        event = SyncEvent(
            event_type="update_chat",
            source="pdf",
            data={"message": message}
        )
        self.emit(event)

    def clear_all_highlights(self):
        event = SyncEvent(
            event_type="clear_highlights",
            source="system",
            data={}
        )
        self.emit(event)
        self._state["highlighted_regions"] = []
        self._state["current_step"] = None

    def enable_sync(self, enabled: bool = True):
        self._state["sync_enabled"] = enabled
        logger.info(f"Sync {'enabled' if enabled else 'disabled'}")

    def get_state(self) -> dict:
        return self._state.copy()

    def get_event_history(self, event_type: str = None) -> list[SyncEvent]:
        if event_type:
            return [e for e in self.event_history if e.event_type == event_type]
        return self.event_history.copy()

    def _get_step_color(self, step_num: int) -> str:
        colors = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7", "#DDA0DD", "#98D8C8"]
        return colors[(step_num - 1) % len(colors)]
