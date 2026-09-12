from __future__ import annotations

import hashlib
import logging
import os

from dotenv import load_dotenv
from groq import Groq
from langsmith import traceable

from crm.providers.base import EmbedderError

log = logging.getLogger(__name__)

_DIMENSION = 768


def _local_embed(text: str, dimension: int) -> list[float]:
    vec = [0.0] * dimension
    for raw in (text or "").lower().split():
        token = raw.strip(".,!?;:\"'")
        if not token:
            continue
        digest = hashlib.md5(token.encode()).digest()
        vec[digest[0] % dimension] += 1.0
        vec[digest[1] % dimension] += 0.5
    mag = sum(x * x for x in vec) ** 0.5
    return [x / mag for x in vec] if mag else vec


class GroqEmbedder:
    dimension = _DIMENSION

    def __init__(self, *, api_key: str, model: str | None = None) -> None:
        self._api_key = api_key
        self._model = model or os.environ.get("CRM_EMBED_MODEL")

    @classmethod
    def from_env(cls) -> GroqEmbedder:
        load_dotenv()
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise EmbedderError("missing environment variable: GROQ_API_KEY")
        return cls(api_key=api_key)

    @traceable(name="embed")
    def embed(self, text: str) -> list[float]:
        if self._model:
            try:
                response = Groq(api_key=self._api_key).embeddings.create(
                    input=text, model=self._model
                )
                vector = response.data[0].embedding
                if not vector:
                    raise EmbedderError("empty embedding")
                return list(vector)
            except EmbedderError:
                raise
            except Exception as exc:
                if "model_not_found" not in str(exc) and "does not exist" not in str(exc):
                    raise EmbedderError(str(exc)) from exc
                log.warning(
                    "Groq embeddings unavailable (%s); using local token hash",
                    exc,
                )
        return _local_embed(text, self.dimension)
