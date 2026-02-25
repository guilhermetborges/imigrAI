import enum
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base
from apps.common.models import CreatedAtMixin, UUIDPrimaryKeyMixin


class SourceType(enum.StrEnum):
    html = "html"
    pdf = "pdf"
    api = "api"


class IngestionRunTrigger(enum.StrEnum):
    scheduled = "scheduled"
    manual = "manual"
    reprocess = "reprocess"


class IngestionRunStatus(enum.StrEnum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    quarantined = "quarantined"


class IngestionRunItemStatus(enum.StrEnum):
    pending = "pending"
    running = "running"
    skipped = "skipped"
    completed = "completed"
    failed = "failed"
    manual_review = "manual_review"
    quarantined = "quarantined"


class ParserMode(enum.StrEnum):
    deterministic = "deterministic"
    llm_fallback = "llm_fallback"


class SourceRegistry(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "source_registry"
    __table_args__ = (UniqueConstraint("source_key", name="uq_source_registry_source_key"),)

    source_key: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    country_code: Mapped[str] = mapped_column(String(2), nullable=False, index=True)
    country_name: Mapped[str] = mapped_column(String(120), nullable=False)
    program_code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    program_name: Mapped[str] = mapped_column(String(160), nullable=False)
    source_type: Mapped[SourceType] = mapped_column(
        Enum(SourceType, name="source_type"),
        nullable=False,
    )
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    robots_url: Mapped[str | None] = mapped_column(Text)
    terms_url: Mapped[str | None] = mapped_column(Text)
    schedule_cron: Mapped[str | None] = mapped_column(String(64))
    parser_name: Mapped[str] = mapped_column(String(64), nullable=False, default="deterministic-v1")
    parser_version: Mapped[str] = mapped_column(String(32), nullable=False, default="1.0.0")
    confidence_threshold: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False, default=0.80)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    quarantine_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    quarantine_reason: Mapped[str | None] = mapped_column(Text)
    consecutive_failures: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    metadata_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    run_items: Mapped[list["IngestionRunItem"]] = relationship(back_populates="source")
    bronze_documents: Mapped[list["BronzeDocument"]] = relationship(back_populates="source")
    source_documents: Mapped[list["SourceDocument"]] = relationship(back_populates="source")


class IngestionRun(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "ingestion_run"

    trigger_type: Mapped[IngestionRunTrigger] = mapped_column(
        Enum(IngestionRunTrigger, name="ingestion_run_trigger"),
        nullable=False,
        default=IngestionRunTrigger.scheduled,
    )
    status: Mapped[IngestionRunStatus] = mapped_column(
        Enum(IngestionRunStatus, name="ingestion_run_status"),
        nullable=False,
        default=IngestionRunStatus.pending,
        index=True,
    )
    requested_by: Mapped[str | None] = mapped_column(String(120))
    trace_id: Mapped[str | None] = mapped_column(String(64), index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    total_items: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    processed_items: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    success_items: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_items: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    notes: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    items: Mapped[list["IngestionRunItem"]] = relationship(back_populates="run")


class IngestionRunItem(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "ingestion_run_item"
    __table_args__ = (
        UniqueConstraint(
            "ingestion_run_id",
            "source_id",
            name="uq_ingestion_run_item_source_once",
        ),
    )

    ingestion_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("ingestion_run.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_id: Mapped[UUID] = mapped_column(
        ForeignKey("source_registry.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    status: Mapped[IngestionRunItemStatus] = mapped_column(
        Enum(IngestionRunItemStatus, name="ingestion_run_item_status"),
        nullable=False,
        default=IngestionRunItemStatus.pending,
        index=True,
    )
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    collected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fetch_etag: Mapped[str | None] = mapped_column(String(120))
    fetch_last_modified: Mapped[str | None] = mapped_column(String(120))
    raw_hash_sha256: Mapped[str | None] = mapped_column(String(64), index=True)
    semantic_hash_sha256: Mapped[str | None] = mapped_column(String(64), index=True)
    parser_used: Mapped[str | None] = mapped_column(String(64))
    parser_mode: Mapped[ParserMode] = mapped_column(
        Enum(ParserMode, name="ingestion_parser_mode"),
        nullable=False,
        default=ParserMode.deterministic,
    )
    confidence_score: Mapped[float | None] = mapped_column(Numeric(5, 4))
    manual_review_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    error_message: Mapped[str | None] = mapped_column(Text)
    diff_summary_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    metadata_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    run: Mapped["IngestionRun"] = relationship(back_populates="items")
    source: Mapped["SourceRegistry"] = relationship(back_populates="run_items")
    bronze_document: Mapped["BronzeDocument | None"] = relationship(back_populates="run_item")
    silver_sections: Mapped[list["SilverSection"]] = relationship(back_populates="run_item")
    source_document: Mapped["SourceDocument | None"] = relationship(back_populates="run_item")


class BronzeDocument(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "bronze_document"
    __table_args__ = (
        UniqueConstraint(
            "ingestion_run_item_id",
            name="uq_bronze_document_run_item",
        ),
    )

    source_id: Mapped[UUID] = mapped_column(
        ForeignKey("source_registry.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ingestion_run_item_id: Mapped[UUID] = mapped_column(
        ForeignKey("ingestion_run_item.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(120))
    content_length: Mapped[int | None] = mapped_column(Integer)
    storage_bucket: Mapped[str] = mapped_column(
        String(120), nullable=False, default="ingestion-bronze"
    )
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    storage_uri: Mapped[str] = mapped_column(Text, nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    metadata_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    source: Mapped["SourceRegistry"] = relationship(back_populates="bronze_documents")
    run_item: Mapped["IngestionRunItem"] = relationship(back_populates="bronze_document")


class SilverSection(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "silver_section"
    __table_args__ = (
        UniqueConstraint(
            "ingestion_run_item_id",
            "section_key",
            name="uq_silver_section_item_key",
        ),
    )

    ingestion_run_item_id: Mapped[UUID] = mapped_column(
        ForeignKey("ingestion_run_item.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    section_key: Mapped[str] = mapped_column(String(64), nullable=False)
    heading: Mapped[str | None] = mapped_column(String(255))
    section_order: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    text_content: Mapped[str] = mapped_column(Text, nullable=False)
    semantic_hash_sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    metadata_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    run_item: Mapped["IngestionRunItem"] = relationship(back_populates="silver_sections")


class SourceDocument(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "source_documents"

    source_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("source_registry.id", ondelete="SET NULL"),
        index=True,
    )
    ingestion_run_item_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("ingestion_run_item.id", ondelete="SET NULL"),
        index=True,
    )
    program_version_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("program_versions.id", ondelete="SET NULL"),
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64), index=True)
    raw_storage_uri: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    metadata_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    source: Mapped["SourceRegistry | None"] = relationship(back_populates="source_documents")
    run_item: Mapped["IngestionRunItem | None"] = relationship(back_populates="source_document")
    program_version: Mapped["ProgramVersion | None"] = relationship(
        back_populates="source_documents"
    )
    extractions: Mapped[list["SourceExtraction"]] = relationship(back_populates="source_document")


class SourceExtraction(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "source_extractions"
    __table_args__ = (
        UniqueConstraint(
            "source_document_id",
            "extraction_version",
            name="uq_source_extractions_document_version",
        ),
    )

    source_document_id: Mapped[UUID] = mapped_column(
        ForeignKey("source_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    extraction_version: Mapped[str] = mapped_column(String(32), nullable=False)
    extracted_text: Mapped[str | None] = mapped_column(Text)
    structured_data_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    confidence_score: Mapped[float | None] = mapped_column(Numeric(5, 4))
    parser_used: Mapped[str | None] = mapped_column(String(64))
    parser_mode: Mapped[ParserMode] = mapped_column(
        Enum(ParserMode, name="ingestion_parser_mode"),
        nullable=False,
        default=ParserMode.deterministic,
    )
    manual_review_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    semantic_hash_sha256: Mapped[str | None] = mapped_column(String(64), index=True)
    extraction_metadata_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    source_document: Mapped["SourceDocument"] = relationship(back_populates="extractions")


if TYPE_CHECKING:
    from apps.immigration_rules.models import ProgramVersion
