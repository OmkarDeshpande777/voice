"""Resume upload database model."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, DateTime, Text, ForeignKey, JSON
from database import Base


class ResumeUpload(Base):
    __tablename__ = "resume_uploads"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    extracted_text = Column(Text, nullable=True)
    extracted_skills = Column(JSON, nullable=True)          # list of skill strings
    predicted_category = Column(String(100), nullable=True)  # e.g. "Data Science"
    recommended_jobs = Column(JSON, nullable=True)           # list of job title strings
    uploaded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
