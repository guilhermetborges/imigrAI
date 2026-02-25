from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SourceDocumentCreate(BaseModel):
    program_version_id: UUID | None = None
    title: str = Field(min_length=2, max_length=255)
    source_url: str
    checksum_sha256: str | None = Field(default=None, min_length=64, max_length=64)
    raw_storage_uri: str | None = None
    published_at: datetime | None = None
    metadata_json: dict = Field(default_factory=dict)


class SourceDocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    program_version_id: UUID | None
    title: str
    source_url: str
    checksum_sha256: str | None
    raw_storage_uri: str | None
    published_at: datetime | None
    metadata_json: dict
    created_at: datetime


class SourceExtractionCreate(BaseModel):
    source_document_id: UUID
    extraction_version: str = Field(min_length=1, max_length=32)
    extracted_text: str | None = None
    structured_data_json: dict = Field(default_factory=dict)
    confidence_score: Decimal | None = None


class SourceExtractionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_document_id: UUID
    extraction_version: str
    extracted_text: str | None
    structured_data_json: dict
    confidence_score: Decimal | None
    created_at: datetime
