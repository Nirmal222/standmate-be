from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, BigInteger, Boolean
from datetime import datetime
from models.base import Base

class User(Base):
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(100), unique=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    
    # Auth fields
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    auth_provider: Mapped[str] = mapped_column(String(50), default="email")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Access Control
    has_access: Mapped[bool] = mapped_column(Boolean, default=False)
    is_waitlisted: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    projects: Mapped[list["Project"]] = relationship("Project", back_populates="user")
