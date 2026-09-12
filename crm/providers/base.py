from typing import Mapping, Protocol, Sequence


class ExtractorError(Exception):
    """Raised when business-card extraction fails."""


class TranscriberError(Exception):
    """Raised when voice transcription fails."""


class CardExtractor(Protocol):
    def extract_card(self, image_path: str) -> dict: ...


class VoiceTranscriber(Protocol):
    def transcribe(self, voice_path: str) -> str: ...


class SearchAnswerer(Protocol):
    def answer(self, query: str, records: Sequence[Mapping]) -> str: ...


class EmbedderError(Exception):
    """Raised when embedding generation fails."""


class EmbeddingProvider(Protocol):
    dimension: int

    def embed(self, text: str) -> list[float]: ...
