"""Resume upload & analysis API routes."""
import os
import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session

from config import UPLOAD_DIR
from database import get_db
from routers.auth import get_current_user
from models.resume import ResumeUpload
from schemas.resume import ResumeAnalysisOut, ResumeQuestionOut
from services.resume_service import (
    analyse_resume,
    generate_resume_questions,
)

router = APIRouter(prefix="/api/resume", tags=["Resume"])

ALLOWED_EXTENSIONS = {".pdf"}


@router.post("/upload", response_model=ResumeAnalysisOut)
async def upload_resume(
    file: UploadFile = File(...),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload a resume PDF, extract skills and predict job category."""
    # Validate file type
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are supported.",
        )

    # Save file
    resume_dir = UPLOAD_DIR / "resumes"
    resume_dir.mkdir(parents=True, exist_ok=True)

    unique_name = f"{uuid.uuid4().hex}{ext}"
    file_path = resume_dir / unique_name

    contents = await file.read()
    with open(file_path, "wb") as f:
        f.write(contents)

    # Analyse
    extracted_text, skills, category, jobs = analyse_resume(str(file_path))
    if extracted_text is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Could not extract text from the uploaded PDF.",
        )

    # Persist
    record = ResumeUpload(
        user_id=current_user.id,
        filename=file.filename,
        extracted_text=extracted_text,
        extracted_skills=skills,
        predicted_category=category,
        recommended_jobs=jobs,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return ResumeAnalysisOut.model_validate(record)


@router.get("/latest", response_model=ResumeAnalysisOut)
def get_latest_resume(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return the most recently uploaded resume analysis for the current user."""
    record = (
        db.query(ResumeUpload)
        .filter(ResumeUpload.user_id == current_user.id)
        .order_by(ResumeUpload.uploaded_at.desc())
        .first()
    )
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No resume found. Please upload one first.",
        )
    return ResumeAnalysisOut.model_validate(record)


@router.get("/questions", response_model=List[ResumeQuestionOut])
def get_resume_questions(
    count: int = 5,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate interview questions based on the user's latest resume."""
    record = (
        db.query(ResumeUpload)
        .filter(ResumeUpload.user_id == current_user.id)
        .order_by(ResumeUpload.uploaded_at.desc())
        .first()
    )
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No resume found. Please upload one first.",
        )

    questions = generate_resume_questions(
        skills=record.extracted_skills or [],
        category=record.predicted_category or "General",
        count=count,
    )
    return [ResumeQuestionOut(**q) for q in questions]
