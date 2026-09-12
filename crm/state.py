from typing import Literal, TypedDict


class CRMState(TypedDict):
    name: str | None
    image_path: str | None
    voice_path: str | None
    status: Literal["pending", "loaded", "valid", "invalid", "complete"]
    errors: list[str]
