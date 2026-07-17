from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

if TYPE_CHECKING:
    from app.models.sql.document import DocumentVersion
    from app.models.sql.node import LogicalNode
    from app.models.sql.generated_test_case import GeneratedTestCase


class Selection(Base):
    """
    Represents a user selection (e.g. annotations, highlights) pinned to a specific document version.
    """
    __tablename__ = "selections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    document_version_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("document_versions.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    document_version: Mapped["DocumentVersion"] = relationship("DocumentVersion", back_populates="selections")
    selection_nodes: Mapped[list["SelectionNode"]] = relationship(
        "SelectionNode", back_populates="selection", cascade="all, delete-orphan"
    )
    generated_test_cases: Mapped[list["GeneratedTestCase"]] = relationship(
        "GeneratedTestCase", back_populates="selection", cascade="all, delete-orphan"
    )


class SelectionNode(Base):
    """
    Many-to-many junction table mapping selections to the logical nodes they contain.
    Supports storing an optional selection text snippet context.
    """
    __tablename__ = "selection_nodes"

    selection_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("selections.id", ondelete="CASCADE"), primary_key=True
    )
    logical_node_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("logical_nodes.id", ondelete="CASCADE"), primary_key=True
    )
    selected_text: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    # Relationships
    selection: Mapped["Selection"] = relationship("Selection", back_populates="selection_nodes")
    logical_node: Mapped["LogicalNode"] = relationship("LogicalNode", back_populates="selection_mappings")
