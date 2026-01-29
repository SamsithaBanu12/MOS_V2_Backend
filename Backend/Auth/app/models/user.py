from datetime import datetime
from typing import List
from uuid import UUID, uuid4
from sqlalchemy import String, Boolean, Integer, ForeignKey, Table, Column, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


# Association table for many-to-many relationship between Role and Permission
role_permission = Table(
    "role_permission",
    Base.metadata,
    Column("role_id", Integer, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", Integer, ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True)
)


class Permission(Base):
    """Permission model for RBAC."""
    
    __tablename__ = "permissions"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    
    # Relationships
    roles: Mapped[List["Role"]] = relationship(
        "Role",
        secondary=role_permission,
        back_populates="permissions"
    )
    
    def __repr__(self) -> str:
        return f"<Permission(id={self.id}, name={self.name})>"


class Role(Base):
    """Role model for RBAC."""
    
    __tablename__ = "roles"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    
    # Relationships
    users: Mapped[List["User"]] = relationship("User", back_populates="role")
    permissions: Mapped[List[Permission]] = relationship(
        "Permission",
        secondary=role_permission,
        back_populates="roles"
    )
    
    def __repr__(self) -> str:
        return f"<Role(id={self.id}, name={self.name})>"


class User(Base):
    """User model with authentication and RBAC."""
    
    __tablename__ = "users"
    
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(100), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role_id: Mapped[int] = mapped_column(Integer, ForeignKey("roles.id"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    role: Mapped[Role] = relationship("Role", back_populates="users")
    refresh_tokens: Mapped[List["RefreshToken"]] = relationship(
        "RefreshToken", back_populates="user", cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, username={self.username})>"


class RefreshToken(Base):
    """Model to store and track refresh tokens."""

    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    token: Mapped[str] = mapped_column(String(512), unique=True, nullable=False, index=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="refresh_tokens")
