import pytest
from pydantic import ValidationError

from crm.schemas import ContactEvidence


def test_full_valid_payload() -> None:
    evidence = ContactEvidence.model_validate(
        {
            "full_name": "Ada Lovelace",
            "company": "Analytical Engines",
            "job_title": "Mathematician",
            "email": "ada@example.com",
            "phone": "+44 20 0000 0000",
            "website": "https://ada.example",
            "address": "London",
        }
    )
    assert evidence.full_name == "Ada Lovelace"
    assert evidence.company == "Analytical Engines"
    assert evidence.job_title == "Mathematician"
    assert evidence.email == "ada@example.com"
    assert evidence.phone == "+44 20 0000 0000"
    assert evidence.website == "https://ada.example"
    assert evidence.address == "London"


def test_full_name_required_and_blank_fails() -> None:
    with pytest.raises(ValidationError):
        ContactEvidence.model_validate({})

    with pytest.raises(ValidationError):
        ContactEvidence.model_validate({"full_name": ""})

    with pytest.raises(ValidationError):
        ContactEvidence.model_validate({"full_name": "   "})


def test_omitted_optional_fields_are_null() -> None:
    evidence = ContactEvidence.model_validate({"full_name": "Ada Lovelace"})
    assert evidence.company is None
    assert evidence.job_title is None
    assert evidence.email is None
    assert evidence.phone is None
    assert evidence.website is None
    assert evidence.address is None


def test_empty_optional_strings_normalize_to_null() -> None:
    evidence = ContactEvidence.model_validate(
        {
            "full_name": "Ada Lovelace",
            "company": "",
            "job_title": "   ",
            "email": "",
            "phone": "",
            "website": "",
            "address": "",
        }
    )
    assert evidence.company is None
    assert evidence.job_title is None
    assert evidence.email is None
    assert evidence.phone is None
    assert evidence.website is None
    assert evidence.address is None


def test_no_email_or_phone_format_validators() -> None:
    evidence = ContactEvidence.model_validate(
        {
            "full_name": "Ada Lovelace",
            "email": "not-an-email",
            "phone": "call me maybe",
        }
    )
    assert evidence.email == "not-an-email"
    assert evidence.phone == "call me maybe"
