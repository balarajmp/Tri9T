from datetime import datetime
from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class LLMGenerationFailure(Base):
    """
    Stores logs of failed LLM generation runs that failed Pydantic schema validation
    after all retry attempts.
    """
    __tablename__ = "llm_generation_failures"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    selection_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    error_message: Mapped[str] = mapped_column(String(1000), nullable=False)
    raw_response: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
