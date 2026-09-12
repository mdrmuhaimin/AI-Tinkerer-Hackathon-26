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
