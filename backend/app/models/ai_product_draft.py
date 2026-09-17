import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.ai import AIRequestStatus


class AIProductDraft(Base):
    """An AI-proposed product, held for admin review.

    Nothing here is a Product yet: the draft is what the admin sees on the
    review screen, and only confirming it runs the normal product creation
    path. Deliberately reuses AIRequestStatus rather than declaring a second
    status enum, so Postgres keeps one `ai_request_status` type.
    """

    __tablename__ = "ai_product_drafts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    admin_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    requested_name: Mapped[str] = mapped_column(String(200), nullable=False)

    # What the model found on the web. source_url is kept for provenance —
    # the image is someone else's photo, so where it came from is worth
    # being able to answer later.
    source_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    source_title: Mapped[str | None] = mapped_column(String(500), nullable=True)

    extracted_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    extracted_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    suggested_price: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)

    # The themed prompt generated for this product, shown to the admin.
    image_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)

    # The processed image, already written to the products upload dir so the
    # admin can preview it before deciding. On confirm it simply becomes the
    # product's image_url — no second copy, no re-upload.
    staged_image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # Whether the processed image actually carries an alpha channel, rather
    # than background removal having quietly returned an opaque picture.
    has_transparency: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # How the image pipeline actually ended. Plain text rather than a database
    # enum: these are reporting states that will change as the pipeline does,
    # and a Postgres enum would need a migration for every new one.
    # See ImageStatus in services/ai_product_service.
    image_status: Mapped[str] = mapped_column(String(30), default="not_attempted", nullable=False)
    image_error: Mapped[str | None] = mapped_column(String(500), nullable=True)

    status: Mapped[AIRequestStatus] = mapped_column(
        Enum(AIRequestStatus, name="ai_request_status"), default=AIRequestStatus.PENDING, nullable=False
    )
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)

    created_product_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    admin: Mapped["User"] = relationship("User", foreign_keys=[admin_id])
    created_product: Mapped["Product | None"] = relationship("Product")
