from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse
from typing import Optional
import asyncio
import json

from database import get_db
from models import Scan
from schemas import (
    ScanCreateRequest,
    ScanCreateResponse,
    ScanStatusResponse,
    ScanResultResponse,
    ScanListResponse
)
from scanner.orchestrator import run_scan
from utils.progress import progress_manager

router = APIRouter()


@router.post("", response_model=ScanCreateResponse)
async def create_scan(
    request: ScanCreateRequest,
    db: Session = Depends(get_db)
):
    """Create a new scan. Returns scan_id immediately. Scan runs in background."""
    # Validate URL format
    url = request.url.strip()
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    # Create scan record
    scan = Scan(
        url=url,
        user_brief=request.user_brief,
        tech_stack_input=request.tech_stack,
        test_route=request.test_route,
        status="pending"
    )
    db.add(scan)
    db.commit()
    db.refresh(scan)

    # Launch background task using asyncio.create_task
    asyncio.create_task(
        run_scan(
            scan_id=scan.id,
            api_key=request.api_key,
            llm_provider=request.llm_provider,
            auth_credentials={
                "username": request.auth_username,
                "password": request.auth_password,
                "token": request.auth_token
            } if request.auth_username or request.auth_token else None
        )
    )

    return ScanCreateResponse(id=scan.id, status="pending")


@router.get("/{scan_id}/stream")
async def stream_scan_progress(scan_id: str, db: Session = Depends(get_db)):
    """SSE endpoint for real-time progress updates."""
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    async def event_generator():
        async for event in progress_manager.subscribe(scan_id):
            yield event

    return EventSourceResponse(event_generator())


@router.get("/{scan_id}", response_model=ScanResultResponse)
async def get_scan(scan_id: str, db: Session = Depends(get_db)):
    """Get scan results."""
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    return ScanResultResponse(
        id=scan.id,
        status=scan.status,
        url=scan.url,
        verdict=scan.verdict,
        overall_score=scan.overall_score,
        overall_grade=scan.overall_grade,
        lens_scores=scan.lens_scores,
        findings_count=scan.findings_count,
        top_3_actions=scan.top_3_actions,
        duration_seconds=scan.duration_seconds,
        created_at=scan.created_at,
        completed_at=scan.completed_at,
        error_message=scan.error_message,
        report_a_available=scan.report_a_path is not None,
        report_b_available=scan.report_b_path is not None,
        warnings=scan.warnings
    )


@router.get("", response_model=ScanListResponse)
async def list_scans(
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """List all past scans, ordered by created_at desc."""
    scans = db.query(Scan)\
        .order_by(Scan.created_at.desc())\
        .offset(offset)\
        .limit(limit)\
        .all()

    return ScanListResponse(
        scans=[
            ScanResultResponse(
                id=s.id,
                status=s.status,
                url=s.url,
                verdict=s.verdict,
                overall_score=s.overall_score,
                overall_grade=s.overall_grade,
                lens_scores=s.lens_scores,
                findings_count=s.findings_count,
                top_3_actions=s.top_3_actions,
                duration_seconds=s.duration_seconds,
                created_at=s.created_at,
                completed_at=s.completed_at,
                report_a_available=s.report_a_path is not None,
                report_b_available=s.report_b_path is not None,
                warnings=s.warnings
            )
            for s in scans
        ]
    )
