import logging
import os
import sys
from backend.config import settings


def setup_logging():
    os.makedirs(settings.LOG_DIR, exist_ok=True)
    log_file = os.path.join(settings.LOG_DIR, settings.LOG_FILE)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)

    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    ))

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(logging.Formatter(
        "%(levelname)-8s | %(message)s"
    ))

    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    logging.getLogger("streamlit").setLevel(logging.WARNING)
    logging.getLogger("sentence_transformers").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def log_event(event_type: str, user_id: str, details: dict = None):
    logger = logging.getLogger("audit")
    msg = f"[{event_type}] user={user_id}"
    if details:
        detail_str = " | ".join(f"{k}={v}" for k, v in details.items())
        msg += f" | {detail_str}"
    logger.info(msg)
