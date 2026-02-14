from sqlalchemy import Column, String, Integer, Float, DateTime, JSON, Text
from database import Base
import datetime
import uuid


class Scan(Base):
    __tablename__ = "scans"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.datetime.utcnow)

    # Input
    url = Column(String, nullable=False)
    user_brief = Column(Text, nullable=True)
    tech_stack_input = Column(String, nullable=True)
    test_route = Column(Text, nullable=True)
    uploaded_files = Column(JSON, nullable=True)

    # Auth (for protected routes)
    auth_type = Column(String, nullable=True)

    # Status
    status = Column(String, default="pending")
    current_step = Column(String, nullable=True)
    progress_message = Column(String, nullable=True)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, nullable=True)

    # Results
    verdict = Column(String, nullable=True)
    overall_score = Column(Integer, nullable=True)
    overall_grade = Column(String, nullable=True)
    lens_scores = Column(JSON, nullable=True)
    findings_count = Column(JSON, nullable=True)
    top_3_actions = Column(JSON, nullable=True)

    # Pipeline metadata
    intent_analysis = Column(JSON, nullable=True)
    tech_stack_detected = Column(JSON, nullable=True)
    prompt_versions = Column(JSON, nullable=True)

    # Report file paths
    report_a_path = Column(String, nullable=True)
    report_b_path = Column(String, nullable=True)
    screenshots_dir = Column(String, nullable=True)
