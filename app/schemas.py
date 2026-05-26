import ipaddress
import re
import uuid
from datetime import datetime
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from typing import Optional


def _validate_url_list(v: Optional[list[str]]) -> Optional[list[str]]:
    if v is None:
        return v

    validated: list[str] = []
    for item in v:
        url = str(item)
        parsed = urlparse(url)

        if parsed.scheme not in ("http", "https"):
            raise ValueError(f"Only http/https URLs are allowed: {url!r}")

        if not parsed.netloc:
            raise ValueError(f"URL must include a host: {url!r}")

        if "@" in parsed.netloc:
            raise ValueError("Credentials are not allowed in social link URLs")

        hostname = (parsed.hostname or "").lower()
        if hostname in ("localhost", "::1", "127.0.0.1"):
            raise ValueError("Localhost URLs are not allowed")

        try:
            ip = ipaddress.ip_address(hostname)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                raise ValueError("Private/loopback IP addresses are not allowed")
        except ValueError as exc:
            if "not allowed" in str(exc):
                raise

        if re.search(r"(--|;|/\*|\*/)", url):
            raise ValueError("Potentially dangerous characters in URL")

        validated.append(url)

    return validated


class ClientCreate(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=255)
    last_name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    description: Optional[str] = None
    social_links: Optional[list[str]] = None

    @field_validator("social_links", mode="before")
    @classmethod
    def validate_social_links(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        return _validate_url_list(v)


class ClientUpdate(BaseModel):
    first_name: Optional[str] = Field(None, min_length=1, max_length=255)
    last_name: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    description: Optional[str] = None
    social_links: Optional[list[str]] = None

    @field_validator("social_links", mode="before")
    @classmethod
    def validate_social_links(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        return _validate_url_list(v)


class ClientResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    first_name: str
    last_name: str
    email: str
    description: Optional[str]
    social_links: Optional[list[str]]
    created_at: datetime
    updated_at: datetime


class DocumentCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=1)
    doc_type: Optional[str] = Field(None, max_length=100)


class DocumentUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    content: Optional[str] = Field(None, min_length=1)
    doc_type: Optional[str] = Field(None, max_length=100)


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    client_id: uuid.UUID
    title: str
    content: str
    doc_type: Optional[str]
    summary: Optional[str]
    created_at: datetime
    updated_at: datetime


class ClientSearchResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    client: ClientResponse
    score: float = 0.0


class SearchResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    document: DocumentResponse
    keyword_score: float = 0.0
    semantic_score: float = 0.0
    combined_score: float = 0.0


class SearchResponse(BaseModel):
    query: str
    total: int
    clients: list[ClientSearchResult] = Field(default_factory=list)
    results: list[SearchResult] = Field(default_factory=list)


class SummaryResponse(BaseModel):
    document_id: uuid.UUID
    summary: str
