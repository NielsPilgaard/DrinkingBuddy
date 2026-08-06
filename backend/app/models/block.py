import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Block(Base):
    __tablename__ = "blocks"
    __table_args__ = (UniqueConstraint("blocker_id", "blocked_id"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    blocker_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    blocked_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
