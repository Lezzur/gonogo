# Report Feed Service

Prepares Report A for consumption by Claude Code in the fix loop.

## Usage

```python
from backend.services.report_feed import (
    filter_report_by_severity,
    estimate_token_count,
    prepare_feed,
    generate_delta_report
)

# Filter report by severity
filtered_report = filter_report_by_severity(
    report_a_path="reports/scan_123/report_a.md",
    severities=["critical", "high"]
)

# Estimate token count
token_count = estimate_token_count(filtered_report)
print(f"Estimated tokens: {token_count}")

# Prepare feed (convenience wrapper)
feed_content = prepare_feed(
    report_a_path="reports/scan_123/report_a.md",
    severities=["critical", "high", "medium"]
)

# Generate delta report between scans
current_findings = [
    {"id": "FUNC-001", "title": "Issue 1", "severity": "critical"},
    {"id": "FUNC-002", "title": "Issue 2", "severity": "high"},
]
previous_findings = [
    {"id": "FUNC-001", "title": "Issue 1", "severity": "critical"},
    {"id": "FUNC-003", "title": "Old issue", "severity": "medium"},
]

delta = generate_delta_report(current_findings, previous_findings)
# Returns:
# {
#     "resolved": [{"id": "FUNC-003", ...}],
#     "new": [{"id": "FUNC-002", ...}],
#     "unchanged": [{"id": "FUNC-001", ...}],
#     "resolved_count": 1,
#     "new_count": 1,
#     "unchanged_count": 1
# }
```

## Functions

### `filter_report_by_severity(report_a_path: str, severities: List[str]) -> str`
Filters Report A by severity levels. Always includes the header section (verdict, score, tech stack, date).

**Args:**
- `report_a_path`: Path to the full Report A markdown file
- `severities`: List of severity levels to include (case-insensitive: "critical", "high", "medium", "low")

**Returns:**
- Filtered markdown string with header + selected severity sections

### `estimate_token_count(text: str) -> int`
Rough token estimation using character count (len(text) / 4).

**Args:**
- `text`: Input text

**Returns:**
- Estimated token count

### `prepare_feed(report_a_path: str, severities: List[str]) -> str`
Convenience wrapper for `filter_report_by_severity`. Prepares filtered Report A for Claude Code consumption.

**Args:**
- `report_a_path`: Path to Report A
- `severities`: Severity levels to include

**Returns:**
- Filtered report as string

### `generate_delta_report(current_findings: List[dict], previous_findings: List[dict]) -> dict`
Compares findings between two scans by finding ID.

**Args:**
- `current_findings`: Findings from the current scan (list of Finding dicts with "id" key)
- `previous_findings`: Findings from the previous scan (list of Finding dicts with "id" key)

**Returns:**
- Dict with:
  - `resolved`: List of findings present in previous but not in current
  - `new`: List of findings present in current but not in previous
  - `unchanged`: List of findings present in both
  - `resolved_count`: Count of resolved findings
  - `new_count`: Count of new findings
  - `unchanged_count`: Count of unchanged findings

## Report A Structure

Report A follows this structure:

```markdown
# GoNoGo Report A — AI Handoff
# URL: https://example.com
# Verdict: NO-GO
# Score: 45/100 (F)
# Tech Stack: React, Next.js
# Scanned: 2026-02-22

---

## CRITICAL — Fix Before Launch

### CRIT-001: [title]
- **Page:** /
- **Selector:** button[type=submit]
- **Issue:** [description]
- **Console:** [errors]
- **Values:** [raw data like hex colors, measurements]
- **Fix:** [ai_actionable recommendation]
- **File hint:** [likely file path]

---

## HIGH PRIORITY

[Same structure]

---

## MEDIUM PRIORITY

[Same structure]

---

## LOW PRIORITY

[Same structure]
```

The filter extracts sections using regex patterns and preserves the header for context.
