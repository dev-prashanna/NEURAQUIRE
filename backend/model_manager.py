import logging
from threading import Lock
from backend.config import settings

logger = logging.getLogger(__name__)


class ModelManager:
    _instance = None
    _lock = Lock()
    _models = {}

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
            return cls._instance

    def get_model(self, model_name: str = None):
        if model_name is None:
            model_name = settings.EMBEDDING_MODEL

        if model_name not in self._models:
            logger.info(f"Loading model: {model_name}")
            try:
                from sentence_transformers import SentenceTransformer
                self._models[model_name] = SentenceTransformer(model_name)
                logger.info(f"Model loaded: {model_name}")
            except Exception as e:
                logger.error(f"Failed to load model {model_name}: {e}")
                raise RuntimeError(
                    f"Failed to load AI model. Please check your internet connection "
                    f"and try again. Error: {e}"
                ) from e

        return self._models[model_name]

    def encode(self, texts: list, model_name: str = None) -> list:
        model = self.get_model(model_name)
        return model.encode(texts, show_progress_bar=True).tolist()

    def encode_single(self, text: str, model_name: str = None) -> list:
        model = self.get_model(model_name)
        return model.encode([text])[0].tolist()


model_manager = ModelManager()
