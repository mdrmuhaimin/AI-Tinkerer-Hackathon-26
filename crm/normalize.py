import re

_WS = re.compile(r"\s+")


def _strip(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = str(value).strip()
    return stripped or None


def normalize_email(value: str | None) -> str:
    if not value:
        return ""
    return value.strip().lower()


def normalize_name(value: str | None) -> str:
    if not value:
        return ""
    return _WS.sub(" ", value.strip()).casefold()


def normalize_phone(value: str | None) -> str:
    if not value:
        return ""
    original = value.strip()
    digits = "".join(ch for ch in original if ch.isdigit())
    if not digits:
        return ""
    return f"+{digits}" if original.startswith("+") else digits


def normalize_evidence(evidence: dict) -> dict:
    return {
        "full_name": evidence["full_name"].strip(),
        "company": _strip(evidence.get("company")),
        "job_title": _strip(evidence.get("job_title")),
        "email": _strip(evidence.get("email")),
        "phone": _strip(evidence.get("phone")),
        "website": _strip(evidence.get("website")),
        "address": _strip(evidence.get("address")),
        "email_norm": normalize_email(evidence.get("email")),
        "phone_norm": normalize_phone(evidence.get("phone")),
        "name_norm": normalize_name(evidence.get("full_name")),
        "company_norm": normalize_name(evidence.get("company")),
    }
