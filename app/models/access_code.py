from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Boolean, ForeignKey, Integer, BigInteger
from models.base import Base

class AccessCode(Base):
    __tablename__ = "access_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    is_used: Mapped[bool] = mapped_column(Boolean, default=False)
    
    used_by_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=True)
    used_by: Mapped["User"] = relationship("User")
