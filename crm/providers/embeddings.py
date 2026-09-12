from __future__ import annotations

import os

from dotenv import load_dotenv
from groq import Groq
from langsmith import traceable

from crm.providers.base import EmbedderError

_MODEL = "nomic-embed-text-v1.5"
_DIMENSION = 768


class GroqEmbedder:
    dimension = _DIMENSION

    def __init__(self, *, api_key: str, model: str = _MODEL) -> None:
        self._api_key = api_key
        self._model = model

    @classmethod
    def from_env(cls) -> GroqEmbedder:
        load_dotenv()
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise EmbedderError("missing environment variable: GROQ_API_KEY")
        return cls(api_key=api_key)

    @traceable(name="embed")
    def embed(self, text: str) -> list[float]:
        try:
            client = Groq(api_key=self._api_key)
            response = client.embeddings.create(input=text, model=self._model)
            vector = response.data[0].embedding
            if not vector:
                raise EmbedderError("empty embedding")
            return list(vector)
        except EmbedderError:
            raise
        except Exception as exc:
            raise EmbedderError(str(exc)) from exc
