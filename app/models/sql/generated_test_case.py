from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class GeneratedTestCase(Base):
    """
    Stores successfully generated QA test cases associated with a specific user selection.
    """
    __tablename__ = "generated_test_cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    selection_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("selections.id", ondelete="CASCADE"), nullable=False, index=True
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    reference_context: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    # Relationships
    selection: Mapped["Selection"] = relationship("Selection", back_populates="generated_test_cases")
