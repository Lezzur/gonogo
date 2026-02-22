"""GoNoGo TUI — Backend integration bridge.

All backend imports are isolated here so the rest of the TUI can
import from this single module. If backend dependencies are missing,
errors are caught and surfaced cleanly.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator, Optional

_BACKEND_AVAILABLE = False
_IMPORT_ERROR: Optional[str] = None

try:
    from database import SessionLocal, init_db
    from models import Scan, FixCycle
    from schemas import FixLoopStartRequest
    from scanner.orchestrator import run_scan
    from scanner.fix_loop import FixLoopOrchestrator, start_fix_loop
    from utils.progress import progress_manager
    from config import DATABASE_URL, REPORTS_DIR

    _BACKEND_AVAILABLE = True
except ImportError as exc:
    _IMPORT_ERROR = str(exc)


def is_backend_available() -> bool:
    return _BACKEND_AVAILABLE


def get_import_error() -> Optional[str]:
    return _IMPORT_ERROR


def ensure_backend():
    """Raise if backend is not importable."""
    if not _BACKEND_AVAILABLE:
        raise RuntimeError(
            f"Backend dependencies not available: {_IMPORT_ERROR}\n"
            "Make sure you've installed backend requirements and the backend/ "
            "directory is on sys.path."
        )


# --- Database helpers ---

def get_db_session():
    """Get a new SQLAlchemy session."""
    ensure_backend()
    return SessionLocal()


def initialize_database():
    """Create tables / run migrations."""
    ensure_backend()
    init_db()


# --- Scan helpers ---

def create_scan_record(
    url: str,
    user_brief: str = "",
    tech_stack: str = "",
    test_route: str = "",
) -> str:
    """Create a Scan row and return its id."""
    ensure_backend()
    db = SessionLocal()
    try:
        # Normalize URL
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"

        scan = Scan(
            url=url,
            user_brief=user_brief or None,
            tech_stack_input=tech_stack or None,
            test_route=test_route or None,
            status="pending",
        )
        db.add(scan)
        db.commit()
        db.refresh(scan)
        return scan.id
    finally:
        db.close()


async def launch_scan(
    scan_id: str,
    api_key: str,
    llm_provider: str = "gemini",
    auth_credentials: Optional[dict] = None,
) -> None:
    """Launch run_scan as an asyncio task."""
    ensure_backend()
    await run_scan(
        scan_id=scan_id,
        api_key=api_key,
        llm_provider=llm_provider,
        auth_credentials=auth_credentials,
    )


async def subscribe_progress(scan_id: str) -> AsyncGenerator[dict, None]:
    """Yield progress events from the backend progress manager."""
    ensure_backend()
    async for event in progress_manager.subscribe(scan_id):
        yield event


def get_scan(scan_id: str) -> Optional[dict]:
    """Fetch a single scan as a dict."""
    ensure_backend()
    db = SessionLocal()
    try:
        scan = db.query(Scan).filter(Scan.id == scan_id).first()
        if not scan:
            return None
        return _scan_to_dict(scan)
    finally:
        db.close()


def list_scans(limit: int = 50, offset: int = 0) -> list[dict]:
    """List scans ordered by created_at desc."""
    ensure_backend()
    db = SessionLocal()
    try:
        scans = (
            db.query(Scan)
            .order_by(Scan.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        return [_scan_to_dict(s) for s in scans]
    finally:
        db.close()


def get_fix_cycles(scan_id: str) -> list[dict]:
    """Get all fix cycles for a scan."""
    ensure_backend()
    db = SessionLocal()
    try:
        cycles = (
            db.query(FixCycle)
            .filter(FixCycle.scan_id == scan_id)
            .order_by(FixCycle.cycle_number)
            .all()
        )
        return [
            {
                "id": c.id,
                "cycle_number": c.cycle_number,
                "status": c.status,
                "rescan_id": c.rescan_id,
                "files_modified": c.files_modified or [],
                "findings_resolved": c.findings_resolved,
                "findings_new": c.findings_new,
                "findings_unchanged": c.findings_unchanged,
                "cost_usd": c.claude_code_cost_usd,
                "duration_seconds": c.claude_code_duration_seconds,
                "error_message": c.error_message,
                "created_at": str(c.created_at) if c.created_at else None,
                "completed_at": str(c.completed_at) if c.completed_at else None,
            }
            for c in cycles
        ]
    finally:
        db.close()


async def launch_fix_loop(
    scan_id: str,
    repo_path: str,
    api_key: str,
    llm_provider: str = "gemini",
    max_cycles: int = 3,
    stop_on_verdict: str = "GO",
    apply_mode: str = "branch",
    deploy_mode: str = "branch",
    deploy_command: str = "",
    severity_filter: Optional[list[str]] = None,
) -> None:
    """Start the fix loop orchestrator."""
    ensure_backend()
    config = FixLoopStartRequest(
        repo_path=repo_path,
        apply_mode=apply_mode,
        deploy_mode=deploy_mode,
        deploy_command=deploy_command or None,
        max_cycles=max_cycles,
        stop_on_verdict=stop_on_verdict,
        severity_filter=severity_filter,
    )
    orchestrator = await start_fix_loop(
        scan_id=scan_id,
        config=config,
        api_key=api_key,
        llm_provider=llm_provider,
    )
    await orchestrator.run()


# --- Internal ---

def _scan_to_dict(scan: "Scan") -> dict:
    return {
        "id": scan.id,
        "url": scan.url,
        "status": scan.status,
        "verdict": scan.verdict,
        "overall_score": scan.overall_score,
        "overall_grade": scan.overall_grade,
        "lens_scores": scan.lens_scores or {},
        "findings_count": scan.findings_count or {},
        "top_3_actions": scan.top_3_actions or [],
        "duration_seconds": scan.duration_seconds,
        "error_message": scan.error_message,
        "warnings": scan.warnings or [],
        "current_step": scan.current_step,
        "progress_message": scan.progress_message,
        "user_brief": scan.user_brief,
        "tech_stack_input": scan.tech_stack_input,
        "fix_loop_enabled": scan.fix_loop_enabled,
        "fix_branch": scan.fix_branch,
        "current_cycle": scan.current_cycle,
        "parent_scan_id": scan.parent_scan_id,
        "report_a_path": scan.report_a_path,
        "report_b_path": scan.report_b_path,
        "created_at": str(scan.created_at) if scan.created_at else None,
        "completed_at": str(scan.completed_at) if scan.completed_at else None,
    }
