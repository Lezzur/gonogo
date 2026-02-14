from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pathlib import Path

from database import get_db
from models import Scan
from config import SCREENSHOTS_DIR

router = APIRouter()


@router.get("/{scan_id}/reports/{report_type}")
async def download_report(
    scan_id: str,
    report_type: str,
    db: Session = Depends(get_db)
):
    """Download report file. report_type = 'a' (AI handoff) or 'b' (human review)"""
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    if report_type == "a":
        if not scan.report_a_path:
            raise HTTPException(status_code=404, detail="Report A not available")
        report_path = Path(scan.report_a_path)
        filename = f"gonogo_report_a_{scan_id[:8]}.md"
    elif report_type == "b":
        if not scan.report_b_path:
            raise HTTPException(status_code=404, detail="Report B not available")
        report_path = Path(scan.report_b_path)
        filename = f"gonogo_report_b_{scan_id[:8]}.md"
    else:
        raise HTTPException(status_code=400, detail="Invalid report type. Use 'a' or 'b'")

    if not report_path.exists():
        raise HTTPException(status_code=404, detail="Report file not found")

    return FileResponse(
        path=report_path,
        media_type="text/markdown",
        filename=filename
    )


@router.get("/{scan_id}/screenshots/{filename}")
async def get_screenshot(
    scan_id: str,
    filename: str,
    db: Session = Depends(get_db)
):
    """Serve a screenshot image."""
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    # Screenshots are stored in scan-specific subdirectory
    screenshot_path = SCREENSHOTS_DIR / scan_id / filename

    if not screenshot_path.exists():
        raise HTTPException(status_code=404, detail="Screenshot not found")

    # Determine media type
    suffix = screenshot_path.suffix.lower()
    media_types = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp"
    }
    media_type = media_types.get(suffix, "image/png")

    return FileResponse(path=screenshot_path, media_type=media_type)
