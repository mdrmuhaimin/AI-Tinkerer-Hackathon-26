from typing import Protocol


class ExtractorError(Exception):
    """Raised when business-card extraction fails."""


class CardExtractor(Protocol):
    def extract_card(self, image_path: str) -> dict: ...
