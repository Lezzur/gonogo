"""Fix Loop API endpoints — Control the automated scan→fix→redeploy→rescan cycle."""

import asyncio
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from database import get_db
from models import FixCycle, Scan
from schemas import FixCycleResponse, FixLoopStartRequest
from scanner.fix_loop import FixLoopOrchestrator, start_fix_loop
from utils.progress import progress_manager

router = APIRouter()

# Store active orchestrators for control (advance/stop)
_active_orchestrators: dict[str, FixLoopOrchestrator] = {}


# Request/Response schemas
class FixLoopStartResponse(BaseModel):
    fix_loop_id: str
    status: str
    fix_branch: Optional[str] = None
    estimated_cycles: int


class FixLoopAdvanceRequest(BaseModel):
    deploy_url: str


class FixLoopStatusResponse(BaseModel):
    scan_id: str
    current_cycle: int
    max_cycles: int
    status: str
    fix_branch: Optional[str] = None
    cycles: list[FixCycleResponse] = []
    totals: dict


class FixLoopDiffResponse(BaseModel):
    diff_summary: str
    files_changed: list[str]
    additions: int
    deletions: int


class PrerequisiteCheckResponse(BaseModel):
    ready: bool
    issues: list[str]


@router.post("/{scan_id}/fix-loop", response_model=FixLoopStartResponse)
async def start_fix_loop_endpoint(
    scan_id: str,
    request: FixLoopStartRequest,
    db: Session = Depends(get_db),
):
    """Start automated fix loop for a completed scan."""
    # Validate scan exists and is completed
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    if scan.status != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Scan is not completed (status: {scan.status})",
        )
    if not scan.report_a_path:
        raise HTTPException(status_code=400, detail="Scan has no Report A")

    # Check for active fix loop on this scan
    if scan_id in _active_orchestrators:
        raise HTTPException(
            status_code=409,
            detail="Fix loop already active for this scan",
        )

    # Run pre-flight checks
    issues = _check_prerequisites(request.repo_path, request.apply_mode)
    if issues:
        raise HTTPException(
            status_code=400,
            detail=f"Prerequisites not met: {'; '.join(issues)}",
        )

    # Determine fix branch name
    fix_branch = None
    if request.apply_mode == "branch":
        fix_branch = f"gonogo/fix-{scan_id[:8]}"

    # Start the fix loop orchestrator
    orchestrator = await start_fix_loop(
        scan_id=scan_id,
        config=request,
        api_key="",  # Will be loaded from env/config
        llm_provider="gemini",
    )
    _active_orchestrators[scan_id] = orchestrator

    return FixLoopStartResponse(
        fix_loop_id=scan_id,
        status="started",
        fix_branch=fix_branch,
        estimated_cycles=request.max_cycles,
    )


@router.get("/{scan_id}/fix-loop/stream")
async def stream_fix_loop_progress(scan_id: str, db: Session = Depends(get_db)):
    """SSE endpoint for real-time fix loop progress updates.

    Events:
    - cycle_start: { cycle: int, max_cycles: int }
    - fixing: { message: str, cycle: int }
    - deploying: { message: str, cycle: int }
    - rescanning: { message: str, cycle: int }
    - cycle_complete: { cycle: int, delta: { resolved: int, new: int, unchanged: int } }
    - loop_complete: { cycles_completed: int, total_resolved: int, final_score: int }
    - error: { message: str }
    - awaiting_deploy_url: { cycle: int }
    """
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    async def event_generator():
        async for event in progress_manager.subscribe(scan_id):
            # Transform progress events to fix-loop specific format
            yield event

    return EventSourceResponse(event_generator())


@router.get("/{scan_id}/fix-loop/status", response_model=FixLoopStatusResponse)
async def get_fix_loop_status(scan_id: str, db: Session = Depends(get_db)):
    """Get current fix loop status with all cycle records."""
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    # Get all fix cycles for this scan
    fix_cycles = (
        db.query(FixCycle)
        .filter(FixCycle.scan_id == scan_id)
        .order_by(FixCycle.cycle_number)
        .all()
    )

    # Determine overall status
    if scan_id in _active_orchestrators:
        status = "running"
    elif fix_cycles:
        last_cycle = fix_cycles[-1]
        if last_cycle.status == "completed":
            status = "completed"
        elif last_cycle.status == "failed":
            status = "failed"
        else:
            status = last_cycle.status
    else:
        status = "not_started"

    # Calculate totals
    total_cost = sum(c.claude_code_cost_usd or 0 for c in fix_cycles)
    total_resolved = sum(c.findings_resolved or 0 for c in fix_cycles)
    total_duration = sum(c.claude_code_duration_seconds or 0 for c in fix_cycles)

    # Calculate elapsed time
    if fix_cycles:
        first_created = fix_cycles[0].created_at
        last_completed = fix_cycles[-1].completed_at or datetime.now(timezone.utc)
        elapsed_seconds = (last_completed - first_created).total_seconds()
    else:
        elapsed_seconds = 0

    return FixLoopStatusResponse(
        scan_id=scan_id,
        current_cycle=scan.current_cycle or 0,
        max_cycles=scan.max_cycles or 3,
        status=status,
        fix_branch=scan.fix_branch,
        cycles=[
            FixCycleResponse(
                id=c.id,
                scan_id=c.scan_id,
                cycle_number=c.cycle_number,
                rescan_id=c.rescan_id,
                status=c.status,
                claude_code_output=c.claude_code_output,
                claude_code_cost_usd=c.claude_code_cost_usd,
                claude_code_duration_seconds=c.claude_code_duration_seconds,
                files_modified=c.files_modified,
                findings_resolved=c.findings_resolved or 0,
                findings_new=c.findings_new or 0,
                findings_unchanged=c.findings_unchanged or 0,
                created_at=c.created_at,
                completed_at=c.completed_at,
                error_message=c.error_message,
            )
            for c in fix_cycles
        ],
        totals={
            "cost_usd": round(total_cost, 4),
            "findings_resolved": total_resolved,
            "elapsed_seconds": round(elapsed_seconds, 1),
            "claude_code_duration_seconds": round(total_duration, 1),
        },
    )


@router.post("/{scan_id}/fix-loop/advance")
async def advance_fix_loop(
    scan_id: str,
    request: FixLoopAdvanceRequest,
    db: Session = Depends(get_db),
):
    """Provide deploy URL for manual deploy mode.

    Only valid when deploy_mode="manual" and loop is awaiting URL.
    """
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    if scan.deploy_mode != "manual":
        raise HTTPException(
            status_code=400,
            detail="Advance endpoint only valid for deploy_mode='manual'",
        )

    orchestrator = _active_orchestrators.get(scan_id)
    if not orchestrator:
        raise HTTPException(
            status_code=400,
            detail="No active fix loop for this scan",
        )

    try:
        await orchestrator.advance(request.deploy_url)
        return {"status": "advanced", "deploy_url": request.deploy_url}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{scan_id}/fix-loop/diff", response_model=FixLoopDiffResponse)
async def get_fix_loop_diff(scan_id: str, db: Session = Depends(get_db)):
    """Get git diff summary for branch mode fixes."""
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    if scan.apply_mode != "branch":
        raise HTTPException(
            status_code=400,
            detail="Diff only available for apply_mode='branch'",
        )

    if not scan.fix_branch or not scan.repo_path:
        raise HTTPException(
            status_code=400,
            detail="Fix branch or repo path not set",
        )

    repo_path = Path(scan.repo_path)
    if not repo_path.exists():
        raise HTTPException(status_code=400, detail="Repository path not found")

    try:
        # Get diff stat
        result = subprocess.run(
            ["git", "diff", "--stat", "HEAD~1"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=30,
        )
        diff_stat = result.stdout if result.returncode == 0 else ""

        # Get changed files
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD~1"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=30,
        )
        files_changed = (
            result.stdout.strip().split("\n") if result.returncode == 0 and result.stdout.strip() else []
        )

        # Get addition/deletion counts
        result = subprocess.run(
            ["git", "diff", "--shortstat", "HEAD~1"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=30,
        )
        shortstat = result.stdout.strip() if result.returncode == 0 else ""

        # Parse shortstat (e.g., "3 files changed, 10 insertions(+), 5 deletions(-)")
        additions = 0
        deletions = 0
        if shortstat:
            import re

            ins_match = re.search(r"(\d+) insertion", shortstat)
            del_match = re.search(r"(\d+) deletion", shortstat)
            if ins_match:
                additions = int(ins_match.group(1))
            if del_match:
                deletions = int(del_match.group(1))

        return FixLoopDiffResponse(
            diff_summary=diff_stat,
            files_changed=files_changed,
            additions=additions,
            deletions=deletions,
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=500, detail="Git command timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get diff: {e}")


@router.post("/{scan_id}/fix-loop/stop")
async def stop_fix_loop(scan_id: str, db: Session = Depends(get_db)):
    """Request the fix loop to stop after the current cycle completes."""
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    orchestrator = _active_orchestrators.get(scan_id)
    if not orchestrator:
        raise HTTPException(
            status_code=400,
            detail="No active fix loop for this scan",
        )

    await orchestrator.request_stop()
    return {"status": "stop_requested", "message": "Loop will stop after current cycle completes"}


@router.get("/{scan_id}/fix-loop/check-prerequisites", response_model=PrerequisiteCheckResponse)
async def check_prerequisites(
    scan_id: str,
    repo_path: str,
    apply_mode: str = "branch",
    db: Session = Depends(get_db),
):
    """Pre-flight check before starting fix loop.

    Checks:
    - Claude Code CLI is installed and accessible
    - repo_path exists and is valid
    - If apply_mode="branch", repo is a git repository
    """
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    issues = _check_prerequisites(repo_path, apply_mode)

    return PrerequisiteCheckResponse(
        ready=len(issues) == 0,
        issues=issues,
    )


def _check_prerequisites(repo_path: str, apply_mode: str) -> list[str]:
    """Check prerequisites for fix loop. Returns list of issues."""
    issues = []

    # Check Claude Code CLI is installed
    if not shutil.which("claude"):
        issues.append("Claude Code CLI not found. Install with: npm install -g @anthropic-ai/claude-code")

    # Check repo path exists
    path = Path(repo_path)
    if not path.exists():
        issues.append(f"Repository path does not exist: {repo_path}")
    elif not path.is_dir():
        issues.append(f"Repository path is not a directory: {repo_path}")
    else:
        # Check git repo if branch mode
        if apply_mode == "branch":
            git_dir = path / ".git"
            if not git_dir.exists():
                issues.append(f"Not a git repository (apply_mode='branch'): {repo_path}")

    return issues


def cleanup_orchestrator(scan_id: str):
    """Remove orchestrator from active dict after completion."""
    _active_orchestrators.pop(scan_id, None)
