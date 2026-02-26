"""Pydantic schemas for resume upload feature."""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class ResumeAnalysisOut(BaseModel):
    """Returned after a resume is uploaded and analysed."""
    id: str
    filename: str
    extracted_skills: List[str] = []
    predicted_category: Optional[str] = None
    recommended_jobs: List[str] = []
    uploaded_at: datetime

    model_config = {"from_attributes": True}


class ResumeQuestionOut(BaseModel):
    """A single interview question generated from resume skills."""
    text: str
    difficulty: str = "medium"
    tips: Optional[str] = None
