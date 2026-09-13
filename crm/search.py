from crm.db import ContactStore
from crm.providers.base import EmbeddingProvider

_SEARCH_FIELDS = ("full_name", "company", "job_title", "notes")


def build_search_document(contact: dict) -> str:
    parts = []
    for key in _SEARCH_FIELDS:
        value = contact.get(key)
        if value is not None and str(value).strip():
            parts.append(str(value).strip())
    return " ".join(parts)


def query_contacts(
    store: ContactStore,
    embedder: EmbeddingProvider,
    text: str,
    limit: int = 5,
) -> list[dict]:
    vector = embedder.embed(text)
    hits = store.search_similar(vector, limit)
    results = []
    for contact_id, distance in hits:
        row = store.get(contact_id)
        if row is not None:
            results.append({**row, "distance": distance})
    return results


def _format_query_hits(hits: list[dict]) -> str:
    if not hits:
        return "No matches."
    blocks = []
    for i, hit in enumerate(hits, 1):
        lines = [f"{i}. {hit.get('full_name') or 'Unknown'}"]
        for key in ("company", "job_title"):
            value = hit.get(key)
            if value and str(value).strip():
                lines.append(f"   {value}")
        notes = hit.get("notes")
        if notes and str(notes).strip():
            lines.append("")
            for line in str(notes).splitlines():
                lines.append(f"   {line}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)
