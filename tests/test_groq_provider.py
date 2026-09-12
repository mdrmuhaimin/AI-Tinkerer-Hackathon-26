import pytest

from crm.providers.base import ExtractorError
from crm.providers.groq import GroqCardExtractor


def test_from_env_requires_groq_api_key(monkeypatch) -> None:
    monkeypatch.setattr("crm.providers.groq.load_dotenv", lambda: None)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    with pytest.raises(ExtractorError, match="GROQ_API_KEY"):
        GroqCardExtractor.from_env()


def test_from_env_reads_groq_api_key(monkeypatch) -> None:
    monkeypatch.setattr("crm.providers.groq.load_dotenv", lambda: None)
    monkeypatch.setenv("GROQ_API_KEY", "test-key")

    extractor = GroqCardExtractor.from_env()
    assert extractor._api_key == "test-key"
