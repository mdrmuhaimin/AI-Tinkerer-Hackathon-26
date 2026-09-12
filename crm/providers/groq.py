from __future__ import annotations

import base64
import json
import mimetypes
import os
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq

from crm.providers.base import ExtractorError

# Official Groq vision model with JSON mode:
# https://console.groq.com/docs/vision
_MODEL = "qwen/qwen3.6-27b"

_PROMPT = (
    "Extract contact information from this business card image. "
    "Return a JSON object with keys: full_name, company, job_title, "
    "email, phone, website, address. "
    "Return null when a field is not visible or not supported by the card; "
    "do not guess."
)


def _encode_image(image_path: str) -> tuple[str, str]:
    path = Path(image_path)
    mime = mimetypes.guess_type(path.name)[0] or "image/jpeg"
    with path.open("rb") as image_file:
        encoded = base64.b64encode(image_file.read()).decode("utf-8")
    return mime, encoded


class GroqCardExtractor:
    def __init__(self, *, api_key: str, model: str = _MODEL) -> None:
        self._api_key = api_key
        self._model = model

    @classmethod
    def from_env(cls) -> GroqCardExtractor:
        load_dotenv()
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise ExtractorError("missing environment variable: GROQ_API_KEY")
        return cls(api_key=api_key)

    def extract_card(self, image_path: str) -> dict:
        try:
            mime, encoded = _encode_image(image_path)
            client = Groq(api_key=self._api_key)
            completion = client.chat.completions.create(
                model=self._model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": _PROMPT},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime};base64,{encoded}",
                                },
                            },
                        ],
                    }
                ],
                response_format={"type": "json_object"},
                temperature=1,
                max_completion_tokens=512,
                top_p=1,
                stream=False,
            )
            content = completion.choices[0].message.content
            if not content:
                raise ExtractorError("empty model response")
            parsed = json.loads(content)
            if not isinstance(parsed, dict):
                raise ExtractorError("model response is not a JSON object")
            return parsed
        except ExtractorError:
            raise
        except Exception as exc:
            raise ExtractorError(str(exc)) from exc
