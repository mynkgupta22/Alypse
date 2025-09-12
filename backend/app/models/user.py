from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum, Text, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum

from app.core.database import Base

class UserRole(enum.Enum):
    FREE_USER = "FREE_USER"
    PAID_USER = "PAID_USER"
    ADMIN = "ADMIN"

class User(Base):
    __tablename__="users"

    id = Column(Integer, primary_key=True, index=True)
    google_id = Column(String(100), unique=True, nullable=True, index=True)
    username = Column(String(50),unique=True, index=True, nullable=False)
    full_name = Column(String(100), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.FREE_USER, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
    password_hash = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    emails = relationship("UserEmail", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index('idx_user_role_active', 'role', 'is_active'),
        Index('idx_user_created_at', 'created_at'),
    )


class UserEmail(Base):
    __tablename__ = "user_emails"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    is_primary = Column(Boolean, default=False, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    verification_token = Column(String(255), nullable=True)
    verification_sent_at = Column(DateTime(timezone=True), nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="emails")
    
    # Indexes
    __table_args__ = (
        Index('idx_user_email_user_id', 'user_id'),
        Index('idx_user_email_primary', 'user_id', 'is_primary'),
    )

class UserSession(Base):
    __tablename__ = "user_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    session_token = Column(String(255), unique=True, index=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    ip_address = Column(String(45), nullable=True)  # Support IPv6
    user_agent = Column(Text, nullable=True)
    login_method = Column(String(20), default="password", nullable=False)  # password, google, etc.
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_used_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="sessions")
    
    # Indexes
    __table_args__ = (
        Index('idx_session_user_active', 'user_id', 'is_active'),
        Index('idx_session_expires', 'expires_at'),
    )