from pydantic import BaseModel, field_validator

_OPTIONAL_TEXT_FIELDS = (
    "company",
    "job_title",
    "email",
    "phone",
    "website",
    "address",
)


class ContactEvidence(BaseModel):
    full_name: str
    company: str | None = None
    job_title: str | None = None
    email: str | None = None
    phone: str | None = None
    website: str | None = None
    address: str | None = None

    @field_validator("full_name")
    @classmethod
    def full_name_not_blank(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("full_name must not be blank")
        return value

    @field_validator(*_OPTIONAL_TEXT_FIELDS, mode="before")
    @classmethod
    def empty_optional_to_none(cls, value: object) -> object:
        if value is None:
            return None
        if isinstance(value, str) and not value.strip():
            return None
        return value
