from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base
from apps.common.models import CreatedAtMixin, UUIDPrimaryKeyMixin


class SourceDocument(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "source_documents"

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

    source_document: Mapped["SourceDocument"] = relationship(back_populates="extractions")


if TYPE_CHECKING:
    from apps.immigration_rules.models import ProgramVersion
