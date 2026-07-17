from datetime import datetime
from typing import List
from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class Document(Base):
    """
    Represents the root entity of a document.
    A document can have multiple history versions.
    """
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    versions: Mapped[List["DocumentVersion"]] = relationship(
        "DocumentVersion", back_populates="document", cascade="all, delete-orphan"
    )
    logical_nodes: Mapped[List["LogicalNode"]] = relationship(
        "LogicalNode", back_populates="document", cascade="all, delete-orphan"
    )


class DocumentVersion(Base):
    """
    Tracks the linear history of versions for each document.
    """
    __tablename__ = "document_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    document_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    commit_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="versions")
    node_versions: Mapped[List["NodeVersion"]] = relationship(
        "NodeVersion", back_populates="document_version", cascade="all, delete-orphan"
    )
    selections: Mapped[List["Selection"]] = relationship(
        "Selection", back_populates="document_version", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("document_id", "version_number", name="uq_document_version_number"),
    )
