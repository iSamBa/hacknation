from datetime import datetime

from sqlalchemy import Float, Integer, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Provider(Base):
    __tablename__ = "providers"

    place_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    address: Mapped[str] = mapped_column(String(500))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    rating: Mapped[float] = mapped_column(Float)
    review_count: Mapped[int] = mapped_column(
        Integer, server_default=text("0"), default=0
    )
    is_open: Mapped[bool | None] = mapped_column(nullable=True)
    cached_at: Mapped[datetime] = mapped_column(server_default=func.now())
