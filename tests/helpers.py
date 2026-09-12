import hashlib


class FakeExtractor:
    def __init__(
        self,
        payload: dict | None = None,
        *,
        error: Exception | None = None,
    ) -> None:
        self.payload = payload or {}
        self.error = error
        self.calls: list[str] = []

    def extract_card(self, image_path: str) -> dict:
        self.calls.append(image_path)
        if self.error is not None:
            raise self.error
        return dict(self.payload)


class FakeTranscriber:
    def __init__(
        self,
        transcript: str | None = None,
        *,
        error: Exception | None = None,
    ) -> None:
        self.transcript = transcript or ""
        self.error = error
        self.calls: list[str] = []

    def transcribe(self, voice_path: str) -> str:
        self.calls.append(voice_path)
        if self.error is not None:
            raise self.error
        return self.transcript


class FakeEmbedder:
    dimension = 8

    def __init__(self, *, error: Exception | None = None) -> None:
        self.error = error
        self.calls: list[str] = []

    def embed(self, text: str) -> list[float]:
        self.calls.append(text)
        if self.error is not None:
            raise self.error
        vec = [0.0] * self.dimension
        for raw in text.lower().split():
            token = raw.strip(".,!?;:\"'")
            if not token:
                continue
            digest = hashlib.md5(token.encode()).digest()
            vec[digest[0] % self.dimension] += 1.0
            vec[digest[1] % self.dimension] += 0.5
        mag = sum(x * x for x in vec) ** 0.5
        return [x / mag for x in vec] if mag else vec
