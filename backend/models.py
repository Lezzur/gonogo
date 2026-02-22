from sqlalchemy import Column, String, Integer, Float, DateTime, JSON, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime, timezone
import uuid


class Scan(Base):
    __tablename__ = "scans"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc))

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
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
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

    # Warnings
    warnings = Column(JSON, nullable=True)

    # Fix Loop fields
    fix_loop_enabled = Column(Boolean, default=False)
    fix_branch = Column(String, nullable=True)  # e.g. "gonogo/fix-<short_id>"
    max_cycles = Column(Integer, default=3)
    stop_on_verdict = Column(String, default="GO")  # "GO", "GO_WITH_CONDITIONS", "never"
    current_cycle = Column(Integer, default=0)
    parent_scan_id = Column(String, ForeignKey("scans.id"), nullable=True)
    deploy_mode = Column(String, default="branch")  # "branch", "manual", "local"
    deploy_command = Column(String, nullable=True)
    severity_filter = Column(JSON, nullable=True)  # e.g. ["critical", "high"]
    apply_mode = Column(String, default="branch")  # "branch" or "direct"
    repo_path = Column(String, nullable=True)

    # Relationships
    parent_scan = relationship("Scan", remote_side=[id], backref="rescans")
    fix_cycles = relationship("FixCycle", back_populates="scan", foreign_keys="FixCycle.scan_id")


class FixCycle(Base):
    __tablename__ = "fix_cycles"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    scan_id = Column(String, ForeignKey("scans.id"), nullable=False)  # The original scan
    cycle_number = Column(Integer, nullable=False)
    rescan_id = Column(String, ForeignKey("scans.id"), nullable=True)  # The rescan for this cycle
    status = Column(String, default="pending")  # pending, fixing, deploying, rescanning, completed, failed
    claude_code_output = Column(Text, nullable=True)  # Raw JSON output from Claude Code headless
    claude_code_cost_usd = Column(Float, nullable=True)
    claude_code_duration_seconds = Column(Float, nullable=True)
    files_modified = Column(JSON, nullable=True)  # List of files Claude Code changed
    findings_resolved = Column(Integer, default=0)
    findings_new = Column(Integer, default=0)
    findings_unchanged = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)

    # Relationships
    scan = relationship("Scan", back_populates="fix_cycles", foreign_keys=[scan_id])
    rescan = relationship("Scan", foreign_keys=[rescan_id])
