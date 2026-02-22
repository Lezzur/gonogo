"""
Quick verification script for report_feed.py
"""
from backend.services.report_feed import (
    filter_report_by_severity,
    estimate_token_count,
    prepare_feed,
    generate_delta_report
)


def test_filter_report_by_severity():
    """Test severity filtering."""
    # Create a mock Report A
    mock_report = """# GoNoGo Report A — AI Handoff
# URL: https://example.com
# Verdict: NO-GO
# Score: 45/100 (F)
# Tech Stack: React, Next.js
# Scanned: 2026-02-22

---

## CRITICAL — Fix Before Launch

### CRIT-001: Security header missing
- **Page:** /
- **Selector:** N/A
- **Issue:** Missing Content-Security-Policy header
- **Console:** N/A
- **Values:** N/A
- **Fix:** Add CSP header to server config
- **File hint:** next.config.js

---

## HIGH PRIORITY

### HIGH-001: Broken link
- **Page:** /about
- **Selector:** a[href="/contact"]
- **Issue:** Link returns 404
- **Console:** N/A
- **Values:** N/A
- **Fix:** Update link to correct path
- **File hint:** src/pages/about.tsx

---

## MEDIUM PRIORITY

### MED-001: Contrast issue
- **Page:** /
- **Selector:** .text-gray-400
- **Issue:** Low contrast ratio
- **Console:** N/A
- **Values:** #9CA3AF on #FFFFFF (ratio: 2.8:1)
- **Fix:** Use .text-gray-600 for better contrast
- **File hint:** Search codebase for text-gray-400

---

## LOW PRIORITY

### LOW-001: Missing alt text
- **Page:** /
- **Selector:** img.hero-image
- **Issue:** Image missing alt attribute
- **Console:** N/A
- **Values:** N/A
- **Fix:** Add descriptive alt text
- **File hint:** src/components/Hero.tsx
"""

    # Save mock report
    with open("mock_report_a.md", "w", encoding="utf-8") as f:
        f.write(mock_report)

    # Test 1: Critical only
    result = filter_report_by_severity("mock_report_a.md", ["critical"])
    assert "CRIT-001" in result
    assert "HIGH-001" not in result
    assert "MED-001" not in result
    assert "LOW-001" not in result
    print("✓ Test 1 passed: Critical only")

    # Test 2: Critical + High
    result = filter_report_by_severity("mock_report_a.md", ["critical", "high"])
    assert "CRIT-001" in result
    assert "HIGH-001" in result
    assert "MED-001" not in result
    assert "LOW-001" not in result
    print("✓ Test 2 passed: Critical + High")

    # Test 3: All severities
    result = filter_report_by_severity("mock_report_a.md", ["critical", "high", "medium", "low"])
    assert "CRIT-001" in result
    assert "HIGH-001" in result
    assert "MED-001" in result
    assert "LOW-001" in result
    print("✓ Test 3 passed: All severities")

    # Test 4: Header always included
    result = filter_report_by_severity("mock_report_a.md", ["critical"])
    assert "# GoNoGo Report A" in result
    assert "# Verdict: NO-GO" in result
    assert "# Score: 45/100" in result
    print("✓ Test 4 passed: Header always included")

    # Cleanup
    import os
    os.remove("mock_report_a.md")


def test_estimate_token_count():
    """Test token estimation."""
    text = "Hello world! " * 100  # ~1300 chars
    tokens = estimate_token_count(text)
    assert tokens > 0
    assert tokens == len(text) // 4
    print(f"✓ Token estimation: {len(text)} chars → {tokens} tokens")


def test_prepare_feed():
    """Test prepare_feed wrapper."""
    mock_report = """# Header
---
## CRITICAL — Fix Before Launch
Critical issue
---
## HIGH PRIORITY
High issue
"""
    with open("mock_report_b.md", "w", encoding="utf-8") as f:
        f.write(mock_report)

    result = prepare_feed("mock_report_b.md", ["critical"])
    assert "Critical issue" in result
    assert "High issue" not in result
    print("✓ prepare_feed works correctly")

    import os
    os.remove("mock_report_b.md")


def test_generate_delta_report():
    """Test delta report generation."""
    previous = [
        {"id": "FUNC-001", "title": "Old bug 1", "severity": "critical"},
        {"id": "FUNC-002", "title": "Old bug 2", "severity": "high"},
        {"id": "FUNC-003", "title": "Persistent bug", "severity": "medium"},
    ]

    current = [
        {"id": "FUNC-003", "title": "Persistent bug", "severity": "medium"},
        {"id": "FUNC-004", "title": "New bug 1", "severity": "high"},
        {"id": "FUNC-005", "title": "New bug 2", "severity": "low"},
    ]

    delta = generate_delta_report(current, previous)

    assert delta["resolved_count"] == 2  # FUNC-001, FUNC-002
    assert delta["new_count"] == 2  # FUNC-004, FUNC-005
    assert delta["unchanged_count"] == 1  # FUNC-003

    assert len(delta["resolved"]) == 2
    assert len(delta["new"]) == 2
    assert len(delta["unchanged"]) == 1

    # Verify correct findings are in each category
    resolved_ids = {f["id"] for f in delta["resolved"]}
    assert "FUNC-001" in resolved_ids
    assert "FUNC-002" in resolved_ids

    new_ids = {f["id"] for f in delta["new"]}
    assert "FUNC-004" in new_ids
    assert "FUNC-005" in new_ids

    unchanged_ids = {f["id"] for f in delta["unchanged"]}
    assert "FUNC-003" in unchanged_ids

    print("✓ Delta report generation works correctly")


if __name__ == "__main__":
    print("Running report_feed.py verification tests...\n")
    test_estimate_token_count()
    test_filter_report_by_severity()
    test_prepare_feed()
    test_generate_delta_report()
    print("\n✅ All tests passed!")
