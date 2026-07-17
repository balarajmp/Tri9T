from typing import TYPE_CHECKING
from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

if TYPE_CHECKING:
    from app.models.sql.document import Document, DocumentVersion
    from app.models.sql.selection import SelectionNode


class LogicalNode(Base):
    """
    Maintains a stable logical identity for a structural element (e.g., section, paragraph)
    that persists across multiple document versions.
    """
    __tablename__ = "logical_nodes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    uuid: Mapped[str] = mapped_column(String(36), unique=True, index=True, nullable=False)
    document_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="logical_nodes")
    node_versions: Mapped[list["NodeVersion"]] = relationship(
        "NodeVersion",
        foreign_keys="NodeVersion.logical_node_id",
        back_populates="logical_node",
        cascade="all, delete-orphan"
    )
    child_node_versions: Mapped[list["NodeVersion"]] = relationship(
        "NodeVersion",
        foreign_keys="NodeVersion.parent_logical_node_id",
        back_populates="parent_logical_node",
        cascade="all, delete-orphan"
    )
    selection_mappings: Mapped[list["SelectionNode"]] = relationship(
        "SelectionNode", back_populates="logical_node", cascade="all, delete-orphan"
    )


class NodeVersion(Base):
    """
    Captures the content, metadata, and hierarchical state of a logical node
    at a specific document version.
    """
    __tablename__ = "node_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    logical_node_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("logical_nodes.id", ondelete="CASCADE"), nullable=False
    )
    document_version_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("document_versions.id", ondelete="CASCADE"), nullable=False
    )
    parent_logical_node_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("logical_nodes.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)  # SHA-256 hash of the content
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    logical_node: Mapped[LogicalNode] = relationship(
        LogicalNode, foreign_keys=[logical_node_id], back_populates="node_versions"
    )
    document_version: Mapped["DocumentVersion"] = relationship("DocumentVersion", back_populates="node_versions")
    parent_logical_node: Mapped[LogicalNode | None] = relationship(
        LogicalNode, foreign_keys=[parent_logical_node_id], back_populates="child_node_versions"
    )

    __table_args__ = (
        UniqueConstraint("logical_node_id", "document_version_id", name="uq_node_version_per_doc_version"),
    )
    
    def __repr__(self) -> str:
        return f"<NodeVersion(id={self.id}, title='{self.title}', version_id={self.document_version_id})>"
