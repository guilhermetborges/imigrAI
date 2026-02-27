from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import JSON, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base
from apps.common.models import CreatedAtMixin, UUIDPrimaryKeyMixin


class ProfileMatchSubmission(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "profile_match_submissions"

    user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
    )
    guest_session_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    algorithm_version: Mapped[str] = mapped_column(
        String(32), nullable=False, default="country-fit-v1"
    )
    profile_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    result_json: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=list)
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped["User | None"] = relationship()


if TYPE_CHECKING:
    from apps.accounts.models import User
