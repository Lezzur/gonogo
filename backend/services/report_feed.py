"""
Report Feed Service — Prepares Report A for Claude Code consumption.

Provides filtering, token estimation, and delta analysis for fix loop integration.
"""
import re
from pathlib import Path
from typing import List, Dict, Any


def filter_report_by_severity(report_a_path: str, severities: List[str]) -> str:
    """
    Filter Report A by severity levels.

    Args:
        report_a_path: Path to the full Report A markdown file
        severities: List of severity levels to include (e.g., ["critical", "high"])

    Returns:
        Filtered markdown string with header + selected severity sections
    """
    with open(report_a_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Normalize severity inputs
    severities_normalized = [s.upper() for s in severities]

    # Extract header (everything before the first "---" separator)
    parts = content.split("---", 1)
    if len(parts) < 2:
        # No separators found, return full content
        return content

    header = parts[0]
    body = parts[1]

    # Define severity section patterns
    section_patterns = {
        "CRITICAL": r"## CRITICAL — Fix Before Launch\n(.*?)(?=\n---|\Z)",
        "HIGH": r"## HIGH PRIORITY\n(.*?)(?=\n---|\Z)",
        "MEDIUM": r"## MEDIUM PRIORITY\n(.*?)(?=\n---|\Z)",
        "LOW": r"## LOW PRIORITY\n(.*?)(?=\n---|\Z)"
    }

    # Build filtered report
    filtered_sections = []
    full_content = header + "---" + body

    for severity in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
        if severity in severities_normalized:
            pattern = section_patterns[severity]
            match = re.search(pattern, full_content, re.DOTALL)
            if match:
                section_header = f"## {severity}" if severity != "CRITICAL" else "## CRITICAL — Fix Before Launch"
                filtered_sections.append(f"{section_header}\n{match.group(1).strip()}")

    if not filtered_sections:
        # No matching sections, return header only
        return header

    # Combine header + filtered sections
    return header + "---\n\n" + "\n\n---\n\n".join(filtered_sections) + "\n"


def estimate_token_count(text: str) -> int:
    """
    Rough token estimation using character count.

    Args:
        text: Input text

    Returns:
        Estimated token count (len(text) / 4)
    """
    return len(text) // 4


def prepare_feed(report_a_path: str, severities: List[str]) -> str:
    """
    Prepare filtered Report A for Claude Code consumption.

    Args:
        report_a_path: Path to Report A
        severities: Severity levels to include

    Returns:
        Filtered report as string
    """
    return filter_report_by_severity(report_a_path, severities)


def generate_delta_report(
    current_findings: List[dict],
    previous_findings: List[dict]
) -> dict:
    """
    Compare findings between two scans by ID.

    Args:
        current_findings: Findings from the current scan (list of Finding dicts)
        previous_findings: Findings from the previous scan (list of Finding dicts)

    Returns:
        Dict with:
        - resolved: List of findings present in previous but not in current
        - new: List of findings present in current but not in previous
        - unchanged: List of findings present in both
        - resolved_count: Count of resolved findings
        - new_count: Count of new findings
        - unchanged_count: Count of unchanged findings
    """
    # Build ID sets
    current_ids = {f["id"] for f in current_findings}
    previous_ids = {f["id"] for f in previous_findings}

    # Build ID -> finding maps
    current_map = {f["id"]: f for f in current_findings}
    previous_map = {f["id"]: f for f in previous_findings}

    # Calculate deltas
    resolved_ids = previous_ids - current_ids
    new_ids = current_ids - previous_ids
    unchanged_ids = current_ids & previous_ids

    resolved = [previous_map[fid] for fid in resolved_ids]
    new = [current_map[fid] for fid in new_ids]
    unchanged = [current_map[fid] for fid in unchanged_ids]

    return {
        "resolved": resolved,
        "new": new,
        "unchanged": unchanged,
        "resolved_count": len(resolved),
        "new_count": len(new),
        "unchanged_count": len(unchanged)
    }
