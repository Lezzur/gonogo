# GoNoGo — Full Build Specification

> **What is this document?** This is the complete build specification for GoNoGo, an AI-powered QA and design evaluation agent. It contains everything needed to build the application from scratch: architecture, tech stack, data models, API endpoints, pipeline logic, UI specs, prompt templates, and build order. This document is the single source of truth.

> **How to use this document:** Read it fully before writing any code. Build in the order specified in the Build Order section. Every major decision has been made — do not deviate from the spec without explicit approval.

---

## TABLE OF CONTENTS

1. [Project Overview](#1-project-overview)
2. [Tech Stack](#2-tech-stack)
3. [Repo Structure](#3-repo-structure)
4. [Build Order](#4-build-order)
5. [Data Models & Schemas](#5-data-models--schemas)
6. [Backend API Endpoints](#6-backend-api-endpoints)
7. [Frontend UI Specification](#7-frontend-ui-specification)
8. [The Evaluation Pipeline (10 Steps)](#8-the-evaluation-pipeline-10-steps)
9. [Prompt Templates](#9-prompt-templates)
10. [Report Generation](#10-report-generation)
11. [Configuration & Environment](#11-configuration--environment)
12. [Deployment](#12-deployment)
13. [Strategic Context](#13-strategic-context)
14. [Fix Loop Integration](#14-fix-loop-integration)

---

## 1. PROJECT OVERVIEW

### What GoNoGo Does

GoNoGo is a web application where a user submits a URL (plus optional context), and an AI agent autonomously navigates the site, evaluates it across 7 quality lenses, and produces two downloadable reports:

- **Report A (AI Handoff):** Machine-parseable structured markdown with exact selectors, file path hints, and zero-ambiguity fix instructions. Designed to be pasted into a coding AI (Claude, Cursor, etc.) to implement all fixes.
- **Report B (Human Review):** Rich, visual, contextual report with annotated screenshots, explanations of *why* things matter, and an opinionated but encouraging tone.

Each report includes a **GO / NO-GO / GO WITH CONDITIONS** verdict — the product's signature feature.

### The Name

GoNoGo — from the "go/no-go" decision framework used in aviation and space launches. The final checkpoint before proceeding. Natural CTA: "Run GoNoGo."

### V1 Definition of Done

V1 is successful when: the agent evaluates a real web app → produces a dual report → Report A is handed to a coding AI → the coding AI can act on every finding without asking for clarification → the fixes are correct and useful.

### Who Uses It

- **V1:** Personal tool for the founder (dogfooding on existing BaryApps tools)
- **Future:** Paid tool for vibe coders, solo developers, students. Part of the BaryApps tool suite. BYOK (Bring Your Own Key) model.

---

## 2. TECH STACK

| Layer | Technology | Notes |
|-------|-----------|-------|
| **Frontend** | React + Vite | Lightweight SPA. TypeScript preferred. |
| **Backend** | Python + FastAPI | Async-native. Handles Playwright, LLM calls, subprocess calls to Lighthouse. |
| **Browser Automation** | Playwright (Python) | Headless Chromium. Screenshots, DOM extraction, console capture, network interception. |
| **Job Queue** | For V1: FastAPI BackgroundTasks. Future: Celery + Redis. | Scans are long-running (2–5 min). Cannot block HTTP requests. |
| **Real-time Progress** | Server-Sent Events (SSE) | One-way server→client. Status text updates. |
| **Database** | SQLite (V1) → PostgreSQL (production) | Stores: scan records, metadata, scores, prompt versions used. |
| **File Storage** | Local filesystem (V1) → S3/Cloudflare R2 (production) | Stores: screenshots, report files. |
| **Performance Audit** | Lighthouse CLI | Run via subprocess. Returns JSON report. |
| **Accessibility Audit** | axe-core | Injected via Playwright. Returns JSON violations. |
| **LLM** | Gemini API (primary) | 2.5 Pro for complex steps, 2.5 Flash for simpler steps. BYOK model — user provides their own API key. |
| **LLM (secondary)** | Claude API (Anthropic) | Available as fallback/option. Same BYOK model. |
| **Hosting** | Vercel (frontend) + Railway or VPS (backend) | Backend needs persistent processes for Playwright. Vercel's serverless won't work for 2–5 min scans. |

### Architecture Diagram

```
[React Frontend (Vite)]
        │
        │ REST API + SSE
        ▼
[FastAPI Backend]
        │
        ├── POST /api/scans          → Create scan, return scan_id
        ├── GET  /api/scans/:id/stream → SSE progress feed
        ├── GET  /api/scans/:id        → Get scan results
        ├── GET  /api/scans            → List scan history
        └── GET  /api/scans/:id/reports/:type → Download report
        │
        ▼
[Background Scan Worker]
        │
        ├── Step 0: Playwright + Lighthouse + axe-core (Reconnaissance)
        ├── Step 1: Gemini Pro (Intent Analysis)
        ├── Step 2: Gemini Flash (Tech Stack Detection)
        ├── Steps 3-8: Gemini Pro/Flash (Lens Evaluations — parallel)
        ├── Step 9: Gemini Pro (Synthesis & Scoring)
        └── Step 10: Gemini Pro (Dual Report Generation)
        │
        ▼
[File Storage]              [Database]
Screenshots + Reports       Scan records + metadata
```

---

## 3. REPO STRUCTURE

```
gonogo/
├── README.md
├── .env.example
├── .gitignore
│
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── index.html
│   ├── public/
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── api/                    # API client functions
│       │   └── client.ts
│       ├── components/
│       │   ├── ScanForm.tsx        # URL input, text brief, file upload, tech stack, test route
│       │   ├── ScanProgress.tsx    # SSE progress display
│       │   ├── ScanResults.tsx     # Report display + download buttons
│       │   ├── ScanHistory.tsx     # List of past scans
│       │   ├── ScanComparison.tsx  # Side-by-side scan comparison
│       │   └── Layout.tsx          # Page layout wrapper
│       ├── pages/
│       │   ├── HomePage.tsx        # Landing + scan form
│       │   ├── ScanPage.tsx        # Active scan + results
│       │   └── HistoryPage.tsx     # Scan history + comparison
│       └── styles/
│           └── globals.css
│
├── backend/
│   ├── requirements.txt
│   ├── main.py                     # FastAPI app entry point
│   ├── config.py                   # Environment config
│   ├── database.py                 # SQLite/PostgreSQL setup
│   ├── models.py                   # SQLAlchemy/Pydantic models
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── scans.py                # Scan CRUD endpoints
│   │   └── reports.py              # Report download endpoints
│   │
│   ├── scanner/
│   │   ├── __init__.py
│   │   ├── orchestrator.py         # Main pipeline orchestrator (runs Steps 0–10)
│   │   ├── recon.py                # Step 0: Playwright crawler + Lighthouse + axe-core
│   │   ├── intent.py               # Step 1: Intent analysis
│   │   ├── tech_stack.py           # Step 2: Tech stack detection
│   │   ├── lenses/
│   │   │   ├── __init__.py
│   │   │   ├── functionality.py    # Step 3
│   │   │   ├── design.py           # Step 4
│   │   │   ├── ux.py               # Step 5
│   │   │   ├── performance.py      # Step 6
│   │   │   ├── accessibility.py    # Step 7
│   │   │   └── code_content.py     # Step 8
│   │   ├── synthesis.py            # Step 9: Scoring & deduplication
│   │   └── report_gen.py           # Step 10: Dual report generation
│   │
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── client.py               # Unified LLM client (Gemini primary, Claude secondary)
│   │   └── prompt_loader.py        # Loads versioned prompts from /prompts directory
│   │
│   └── utils/
│       ├── __init__.py
│       ├── screenshots.py          # Screenshot capture and annotation utilities
│       └── progress.py             # SSE progress broadcasting
│
├── prompts/                        # Versioned prompt templates — THIS IS THE PRODUCT'S BRAIN
│   ├── intent_analysis_v1.md
│   ├── tech_stack_detection_v1.md
│   ├── functionality_lens_v1.md
│   ├── design_lens_v1.md
│   ├── ux_lens_v1.md
│   ├── performance_lens_v1.md
│   ├── accessibility_lens_v1.md
│   ├── code_content_lens_v1.md
│   ├── synthesis_v1.md
│   ├── report_a_generation_v1.md
│   ├── report_b_generation_v1.md
│   └── CHANGELOG.md
│
├── fix_loop/                       # Automated fix loop integration
│   ├── claude_code_runner.py      # Claude Code headless invocation
│   ├── fix_orchestrator.py        # Fix cycle orchestration
│   ├── deploy_pipeline.py         # Rebuild/redeploy coordination
│   └── delta_reporter.py          # Inter-cycle delta reporting
│
├── storage/                        # V1 local file storage (gitignored)
│   ├── screenshots/
│   └── reports/
│
└── data/                           # V1 SQLite database (gitignored)
    └── gonogo.db
```

---

## 4. BUILD ORDER

Build in this exact sequence. Each phase produces a testable increment.

### Phase 1: Foundation
1. Initialize the repo with the structure above
2. Set up backend: FastAPI app with health check endpoint
3. Set up frontend: React + Vite scaffold with a basic page
4. Set up database: SQLite with SQLAlchemy, create the Scan model
5. Create `.env.example` with all required env vars
6. Verify: frontend can reach backend API

### Phase 2: Reconnaissance (Step 0) — THE CRITICAL PATH
7. Implement `recon.py` — the Playwright crawler:
   - Accept a URL, crawl and discover pages
   - Page type classification (homepage, listing, detail, form, etc.)
   - Apply exploration depth strategy (deep-test representatives, spot-check, shallow-crawl)
   - Per-page: screenshot (desktop + mobile), DOM snapshot, console capture, network log
   - Stopping rules: max 30 deep, 100 shallow, 10 min timeout
8. Integrate Lighthouse CLI — run via subprocess, parse JSON output
9. Integrate axe-core — inject via Playwright, capture violations
10. Extract: links + status codes, images + alt text, forms, interactive elements, meta tags, framework signatures
11. Build the `recon_data` structured output object
12. Verify: given a URL, produce a complete recon_data JSON + screenshots folder

### Phase 3: LLM Integration
13. Implement `llm/client.py` — unified client for Gemini API (primary) with Claude as secondary
    - Support for text prompts and vision (image) prompts
    - BYOK: read API key from environment variable or per-request config
    - Structured JSON output parsing with validation
    - Retry logic with exponential backoff
14. Implement `llm/prompt_loader.py` — load prompts from `/prompts/` directory, inject dynamic data into `{{placeholders}}`
15. Write all v1 prompt templates (see Section 9)
16. Verify: can send a prompt + screenshot to Gemini and get structured JSON back

### Phase 4: Pipeline Steps 1–2
17. Implement `intent.py` (Step 1) — intent analysis from user brief + screenshots + recon data
18. Implement `tech_stack.py` (Step 2) — tech stack detection from recon heuristics + LLM
19. Verify: given recon_data + user input, produce intent_analysis and tech_stack JSON objects

### Phase 5: Lens Evaluations (Steps 3–8)
20. Implement all 6 lens evaluators, one at a time:
    - `functionality.py` (Step 3) — uses Flash model
    - `design.py` (Step 4) — uses Pro model (vision-heavy)
    - `ux.py` (Step 5) — uses Pro model (vision-heavy)
    - `performance.py` (Step 6) — uses Flash model
    - `accessibility.py` (Step 7) — uses Flash model
    - `code_content.py` (Step 8) — uses Flash model
21. Each lens: takes relevant recon_data subset + intent + tech_stack → returns list of Finding objects
22. Implement parallel execution for Steps 3–8 (asyncio.gather)
23. Verify: given recon_data + intent + tech_stack, each lens produces valid Finding objects

### Phase 6: Synthesis & Reports (Steps 9–10)
24. Implement `synthesis.py` (Step 9) — deduplicate findings, assign priorities, generate scores, determine verdict
25. Implement `report_gen.py` (Step 10) — generate Report A (AI handoff) and Report B (human review) as markdown files
26. Save reports + screenshots to storage
27. Verify: full pipeline produces two downloadable markdown files

### Phase 7: Orchestrator & API
28. Implement `orchestrator.py` — runs Steps 0–10 in sequence, manages state, broadcasts progress via SSE
29. Wire up API endpoints: POST /api/scans (create), GET /api/scans/:id/stream (SSE), GET /api/scans/:id (results), download endpoints
30. Implement scan history: GET /api/scans (list all past scans)
31. Verify: can create a scan via API, watch progress, download reports

### Phase 8: Frontend UI
32. Build `ScanForm.tsx` — the main input form (URL, brief, file upload, tech stack, test route)
33. Build `ScanProgress.tsx` — SSE listener showing status text updates
34. Build `ScanResults.tsx` — display verdict, scores, download buttons for both reports
35. Build `ScanHistory.tsx` — list past scans with scores and verdicts
36. Build `ScanComparison.tsx` — side-by-side score comparison between two scans
37. Wire up routing and layout
38. Verify: end-to-end flow works in browser

### Phase 9: Polish & Hardening
39. Error handling: what happens when a scan fails mid-pipeline? Save partial results, show error state.
40. Input validation: URL format, file size limits, text length limits
41. Add the progress feed toggle (default OFF)
42. Authentication for protected routes: credential form (username/password or token), passed to Playwright
43. Test against 3–5 real sites. Tune prompts based on output quality.

---

## 5. DATA MODELS & SCHEMAS

### Database: Scan Record

```python
# models.py
from sqlalchemy import Column, String, Integer, Float, DateTime, JSON, Text
from sqlalchemy.ext.declarative import declarative_base
import datetime
import uuid

Base = declarative_base()

class Scan(Base):
    __tablename__ = "scans"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.datetime.utcnow)

    # Input
    url = Column(String, nullable=False)
    user_brief = Column(Text, nullable=True)           # Free-form text from user
    tech_stack_input = Column(String, nullable=True)    # User-provided tech stack
    test_route = Column(Text, nullable=True)            # User-specified test route
    uploaded_files = Column(JSON, nullable=True)        # List of uploaded file paths

    # Auth (for protected routes — V1: skip, test public only)
    auth_type = Column(String, nullable=True)           # "credentials" | "token" | null
    # Credentials are NEVER stored in DB — only used during scan and discarded

    # Status
    status = Column(String, default="pending")          # pending | running | completed | failed
    current_step = Column(String, nullable=True)        # e.g., "step_4_design"
    progress_message = Column(String, nullable=True)    # Latest progress text
    error_message = Column(Text, nullable=True)         # Error details if failed
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, nullable=True)

    # Results
    verdict = Column(String, nullable=True)             # "GO" | "NO-GO" | "GO_WITH_CONDITIONS"
    overall_score = Column(Integer, nullable=True)      # 0–100
    overall_grade = Column(String, nullable=True)       # "A+" through "F"
    lens_scores = Column(JSON, nullable=True)           # Per-lens score breakdown
    findings_count = Column(JSON, nullable=True)        # {"critical": 2, "high": 5, ...}
    top_3_actions = Column(JSON, nullable=True)         # Top 3 priority fixes

    # Pipeline metadata
    intent_analysis = Column(JSON, nullable=True)       # Step 1 output
    tech_stack_detected = Column(JSON, nullable=True)   # Step 2 output
    prompt_versions = Column(JSON, nullable=True)       # {"design": "v1", "functionality": "v1", ...}

    # Report file paths
    report_a_path = Column(String, nullable=True)       # Path to AI-consumable report
    report_b_path = Column(String, nullable=True)       # Path to human-readable report
    screenshots_dir = Column(String, nullable=True)     # Path to screenshots directory
```

### Pydantic Schemas (API request/response)

```python
# schemas.py
from pydantic import BaseModel, HttpUrl
from typing import Optional, List
from datetime import datetime

class ScanCreateRequest(BaseModel):
    url: str                                    # Required
    user_brief: Optional[str] = None            # Optional text field
    tech_stack: Optional[str] = None            # Optional tech stack
    test_route: Optional[str] = None            # Optional test route
    api_key: str                                # User's Gemini API key (BYOK)
    llm_provider: str = "gemini"                # "gemini" or "claude"
    # Auth for protected routes (V1: optional, skip for now)
    auth_username: Optional[str] = None
    auth_password: Optional[str] = None
    auth_token: Optional[str] = None

class ScanStatusResponse(BaseModel):
    id: str
    status: str
    current_step: Optional[str]
    progress_message: Optional[str]
    created_at: datetime
    started_at: Optional[datetime]

class ScanResultResponse(BaseModel):
    id: str
    status: str
    url: str
    verdict: Optional[str]
    overall_score: Optional[int]
    overall_grade: Optional[str]
    lens_scores: Optional[dict]
    findings_count: Optional[dict]
    top_3_actions: Optional[list]
    duration_seconds: Optional[float]
    created_at: datetime
    completed_at: Optional[datetime]
    report_a_available: bool
    report_b_available: bool

class ScanListResponse(BaseModel):
    scans: List[ScanResultResponse]
```

### Universal Finding Schema

Every finding from every lens evaluation uses this structure:

```python
class Finding(BaseModel):
    id: str                         # e.g., "FUNC-001", "DESIGN-003"
    lens: str                       # "functionality" | "design" | "ux" | "performance" | "accessibility" | "code_quality" | "content"
    severity: str                   # "critical" | "high" | "medium" | "low"
    effort: str                     # "quick_fix" | "moderate" | "significant"
    confidence: float               # 0.0 – 1.0
    title: str                      # Short description
    description: str                # Detailed explanation

    evidence: Evidence
    recommendation: Recommendation

class Evidence(BaseModel):
    page_url: str                           # e.g., "/checkout"
    screenshot_ref: Optional[str] = None    # Filename of relevant screenshot
    dom_selector: Optional[str] = None      # CSS selector
    console_errors: Optional[List[str]] = None
    network_evidence: Optional[str] = None
    lighthouse_metric: Optional[str] = None
    axe_violation: Optional[str] = None
    raw_data: Optional[dict] = None         # Any additional evidence

class Recommendation(BaseModel):
    human_readable: str     # For Report B — explains why it matters and how to fix
    ai_actionable: str      # For Report A — precise, machine-parseable fix instruction
```

### Recon Data Structure

Output of Step 0 — the raw evidence base for everything else:

```python
class ReconData(BaseModel):
    url: str
    crawled_at: datetime
    pages: List[PageData]
    site_map: dict                          # URL tree structure
    page_type_map: dict                     # {"homepage": ["/"], "product": ["/products/1", ...]}
    lighthouse_report: dict                 # Full Lighthouse JSON
    axe_report: dict                        # Full axe-core JSON
    meta_tags: dict                         # All meta tags from homepage
    og_tags: dict                           # Open Graph tags
    framework_signatures: dict              # Detected frameworks/libraries
    links_audit: List[LinkAudit]            # All links + status codes
    total_pages_found: int
    pages_deep_tested: int
    pages_shallow_crawled: int
    scan_duration_seconds: float

class PageData(BaseModel):
    url: str
    page_type: str                          # "homepage" | "listing" | "detail" | "form" | etc.
    test_depth: str                         # "deep" | "spot_check" | "shallow"
    title: str
    screenshot_desktop: str                 # File path
    screenshot_mobile: str                  # File path
    dom_snapshot: str                       # Full HTML (or path to file)
    console_logs: List[dict]                # {level: "error"|"warning", message: str, source: str}
    network_requests: List[dict]            # {url, status, size, duration, type}
    failed_requests: List[dict]             # Subset of network_requests where status >= 400
    interactive_elements: List[dict]        # {tag, selector, type, text, state}
    form_elements: List[dict]              # {selector, type, label, required, validation}
    images: List[dict]                      # {src, alt, width, height, loaded: bool}
    computed_styles: dict                   # Key elements' computed styles (for design lens)

class LinkAudit(BaseModel):
    url: str
    source_page: str
    status_code: int
    is_internal: bool
    anchor_text: str
```

### Intent Analysis Output (Step 1)

```json
{
  "project_type": "e-commerce store",
  "primary_purpose": "Sell handmade candles direct to consumer",
  "target_audience": {
    "description": "Women 25-40, interested in home decor and self-care",
    "technical_sophistication": "low",
    "expected_familiarity": "first-time visitor"
  },
  "key_user_journeys": [
    "Browse products → View product detail → Add to cart → Checkout",
    "Land on homepage → Understand brand → Browse collection"
  ],
  "success_criteria": [
    "User can find and purchase a product without confusion",
    "Brand identity is clear and consistent"
  ],
  "intent_vs_execution_gaps": [
    "User sketches show a minimalist aesthetic but live site uses 4 different fonts"
  ],
  "confidence": 0.85
}
```

### Tech Stack Output (Step 2)

```json
{
  "framework": "Next.js",
  "ui_library": "Tailwind CSS",
  "language": "TypeScript",
  "hosting_signals": "Vercel",
  "cms": null,
  "notable_libraries": ["Framer Motion", "Stripe"],
  "confidence": 0.9,
  "user_provided_stack": "Next.js, Tailwind, Supabase",
  "discrepancies": []
}
```

### Synthesis & Scoring Output (Step 9)

```json
{
  "overall_score": 72,
  "overall_grade": "C+",
  "verdict": "NO-GO",
  "verdict_reasoning": "Critical functional bugs in the checkout flow make this unsafe to ship.",
  "lens_scores": {
    "functionality": { "score": 45, "grade": "F", "summary": "Critical bugs in core flow" },
    "design": { "score": 78, "grade": "B", "summary": "Good foundations, inconsistent execution" },
    "ux": { "score": 70, "grade": "C+", "summary": "Happy path works, edge cases neglected" },
    "performance": { "score": 82, "grade": "B+", "summary": "Fast, minor optimizations possible" },
    "accessibility": { "score": 60, "grade": "D", "summary": "Multiple WCAG AA failures" },
    "code_quality": { "score": 75, "grade": "B-", "summary": "Clean structure, SEO gaps" },
    "content": { "score": 88, "grade": "A-", "summary": "Well-written, minor typos" }
  },
  "findings_count": { "critical": 2, "high": 5, "medium": 8, "low": 4 },
  "top_3_actions": [
    "Fix the checkout form submission bug (FUNC-001)",
    "Add alt text to product images (A11Y-003)",
    "Reduce hero image size from 2.4MB (PERF-002)"
  ],
  "deduplicated_findings": [ /* all Finding objects, sorted by priority */ ],
  "systemic_patterns": [
    "The app generally lacks loading states across all async operations",
    "Spacing inconsistencies suggest multiple component libraries mixed together"
  ]
}
```

---

## 6. BACKEND API ENDPOINTS

### POST `/api/scans`
Create a new scan. Returns scan_id immediately. Scan runs in background.

**Request:** `ScanCreateRequest` (see schemas above). Files uploaded as multipart form data.

**Response:** `{ "id": "scan_uuid", "status": "pending" }`

**Logic:**
1. Validate URL format
2. Save uploaded files to storage
3. Create Scan record in DB (status: "pending")
4. Launch background task: `orchestrator.run_scan(scan_id)`
5. Return scan_id immediately

### GET `/api/scans/{scan_id}/stream`
SSE endpoint for real-time progress updates.

**Response:** Stream of SSE events:
```
event: progress
data: {"step": "step_0_recon", "message": "Crawling site...", "percent": 10}

event: progress
data: {"step": "step_4_design", "message": "Evaluating design quality...", "percent": 55}

event: complete
data: {"scan_id": "...", "verdict": "NO-GO", "overall_score": 72}

event: error
data: {"message": "Scan failed: unable to reach URL"}
```

### GET `/api/scans/{scan_id}`
Get scan results.

**Response:** `ScanResultResponse`

### GET `/api/scans`
List all past scans, ordered by created_at desc.

**Query params:** `?limit=20&offset=0`

**Response:** `ScanListResponse`

### GET `/api/scans/{scan_id}/reports/{report_type}`
Download report file.

**Params:** `report_type` = `"a"` (AI handoff) or `"b"` (human review)

**Response:** Markdown file download with appropriate headers.

### GET `/api/scans/{scan_id}/screenshots/{filename}`
Serve a screenshot image.

---

## 7. FRONTEND UI SPECIFICATION

### Page: Home / Scan Form

The main page. Clean, focused, single-purpose.

**Layout:**
- Header: "GoNoGo" logo/wordmark + tagline ("Is your app ready to ship?")
- Main form (centered, max-width ~700px):
  1. **URL Input** — large, prominent text field. Placeholder: "https://your-app.com". Required.
  2. **Brief / Instructions** — expandable textarea. Placeholder: "Tell GoNoGo about your project — what it does, who it's for, what to focus on... (optional)". Optional.
  3. **File Upload** — drag/drop zone + click-to-browse. Accepts images (PNG, JPG, WebP, GIF, PDF). Label: "Upload sketches, mockups, notes, or reference images (optional)". Show thumbnails of uploaded files with remove buttons.
  4. **Tech Stack** — small text field. Placeholder: "e.g., Next.js, Tailwind, Supabase (optional)".
  5. **Test Route** — small text field. Placeholder: "e.g., test the checkout flow (optional)". Accompanied by helper text: "You can tell GoNoGo to focus on a specific user flow."
  6. **API Key** — text field (type: password). Placeholder: "Your Gemini API key". Required. Helper text: "Your key is used only for this scan and never stored."
  7. **LLM Provider** — small toggle/select: "Gemini" (default) | "Claude"
  8. **"Run GoNoGo" button** — large, prominent CTA.
- Below form: link to "View Scan History"

**Design notes:** Clean, minimal. The form should feel fast and low-friction. Optional fields should be visually de-emphasized (collapsed or lighter styling) so the MVP experience is: paste URL → paste API key → Run.

### Page: Scan Progress & Results

Shown after clicking "Run GoNoGo".

**While scanning:**
- Large verdict placeholder (grayed out "GO / NO-GO" indicator, waiting)
- Progress section:
  - Current step name: "Evaluating design quality..."
  - Simple progress bar or step indicator (10 steps)
  - **Toggle:** "Show detailed progress" (default OFF). When ON, shows scrolling log of status messages via SSE.
- Estimated time remaining (rough: "Usually takes 2–5 minutes")

**After completion:**
- **Verdict badge** — large, colored: Green "GO" / Red "NO-GO" / Yellow "GO WITH CONDITIONS"
- **Overall score:** "72/100 (C+)"
- **Lens score breakdown:** 7 mini-cards or a horizontal bar chart, one per lens, each showing score + grade + one-line summary
- **Top 3 Actions:** numbered list of the most impactful fixes
- **Download buttons:**
  - "Download Report A (AI Handoff)" → downloads .md file
  - "Download Report B (Full Review)" → downloads .md file
- **Findings summary:** counts by severity (2 critical, 5 high, 8 medium, 4 low)

### Page: Scan History

- Table/list of past scans, newest first
- Each row: URL, date, verdict badge, overall score, duration
- Click a row → goes to that scan's results page
- **Compare button:** select two scans → side-by-side score comparison (per-lens bar charts showing delta)

---

## 8. THE EVALUATION PIPELINE (10 STEPS)

### Step 0: Reconnaissance (No LLM)

**Module:** `scanner/recon.py`

**Purpose:** Gather all raw data before any AI evaluation. This is the foundation.

**Tools:** Playwright (headless Chromium), Lighthouse CLI (subprocess), axe-core (Playwright injection)

**Exploration Depth Strategy:**
1. Crawl and discover all navigable pages from the start URL
2. Categorize each page into a **page type** (homepage, listing, detail, form, settings, dashboard, etc.)
3. **Deep-test** one representative of each page type: full screenshots (desktop 1280px + mobile 375px), DOM snapshot, computed styles, console capture, network log, interact with forms/buttons
4. **Spot-check** 2–3 additional pages per type: screenshots + console + basic checks
5. **Shallow-crawl** everything else: just check for 404s, broken images, console errors

**Stopping rules:**
- Max 30 pages deep-tested
- Max 100 pages shallow-crawled
- Max 10 minutes total scan time
- Done when all page types have a deep-tested representative + all user-specified test routes are walked

**If user specified a test route:** Walk that route step-by-step, capturing state at each step, in addition to the autonomous exploration.

**Lighthouse:** Run on homepage + up to 3 key pages. Parse JSON output.

**axe-core:** Inject on every deep-tested page. Capture violations JSON.

**Output:** Complete `ReconData` object (see data models above).

### Step 1: Intent Analysis (LLM — Gemini Pro)

**Module:** `scanner/intent.py`

**Inputs to LLM:**
- User's text brief (if provided)
- User's uploaded images (if provided) — the LLM should READ any text in these images (handwritten notes, annotations, spec text)
- Homepage screenshot
- Meta tags, OG tags, page titles
- Navigation structure
- First 500 words of visible text content

**Output:** Intent analysis JSON (see data model above)

**Key behavior:** If uploaded images contain sketches/mockups, explicitly compare intent (sketches) vs. reality (live screenshots) and flag discrepancies. This comparison is conceptual, not pixel-level.

### Step 2: Tech Stack Detection (LLM — Gemini Flash + Heuristics)

**Module:** `scanner/tech_stack.py`

**Inputs:**
- User-provided tech stack (if given)
- Framework signatures from recon: script tags, meta generators, CDN URLs, HTTP headers, DOM patterns (`data-reactroot`, `__nuxt`, `wp-content`, etc.)

**Output:** Tech stack JSON (see data model above)

**Cross-reference:** If user provided a tech stack, compare against detected stack and note discrepancies.

### Steps 3–8: Lens Evaluations (Parallel)

**Module:** `scanner/lenses/*.py`

**CRITICAL:** Steps 3–8 can and should run in parallel (asyncio.gather) since they depend only on Steps 0–2, not on each other.

**Each lens:**
1. Receives relevant subset of recon_data + intent_analysis + tech_stack
2. Loads its versioned prompt template from `/prompts/`
3. Sends prompt + data to LLM
4. Parses structured JSON response
5. Validates findings against the Finding schema
6. Returns list of Finding objects

**Model assignment:**
| Step | Lens | Model | Why |
|------|------|-------|-----|
| 3 | Functionality | Flash | Mostly mechanical — interpreting recon data, less creative judgment |
| 4 | Design Quality | **Pro** | Vision-heavy, requires subjective "taste" evaluation |
| 5 | UX Flow | **Pro** | Vision-heavy, requires user empathy and journey analysis |
| 6 | Performance | Flash | Translating Lighthouse metrics into advice — structured, not creative |
| 7 | Accessibility | Flash | Interpreting axe-core output + adding context — structured |
| 8 | Code/Content | Flash | Mix of mechanical detection and moderate subjective evaluation |

**Context window management:** Screenshots are token-expensive. Each lens only receives the screenshots it needs:
- Design: ALL screenshots (desktop + mobile)
- UX: Screenshots in navigation sequence
- Functionality: Only screenshots of error states
- Performance: NONE (works from Lighthouse metrics)
- Accessibility: NONE (works from axe-core data + DOM)
- Code/Content: Homepage screenshot + DOM snapshots only

#### Step 3: Functionality Lens Rubric
- JavaScript console errors (trigger, impact)
- Internal links → 404s, wrong redirects
- External links → broken outbound
- Form submissions (valid + invalid input)
- Interactive elements (buttons, dropdowns, modals)
- Dead ends (no navigation back, actions leading nowhere)
- Broken images
- Progressive enhancement (works without JS?)

#### Step 4: Design Quality Lens Rubric
- Color consistency (coherent palette? clashing?)
- Typography (font families count, size hierarchy H1>H2>H3>body)
- Spacing (consistent rhythm? awkward gaps? cramped?)
- Visual hierarchy (can you tell what's important?)
- Component consistency (cards, buttons, inputs look same throughout?)
- Image quality (crisp, properly sized, consistent style?)
- Overall polish (finished or template-y? default styles left in?)
- Intent vs. execution (if sketches provided, how well does live match?)

#### Step 5: UX Flow Lens Rubric
- First impression / 5-second test (what does this app do? what should I do first?)
- Navigation clarity (logical structure? key pages within 2-3 clicks?)
- CTA clarity (obvious? clear primary action per page?)
- Form UX (good labels, helpful placeholders, clear validation, right input types?)
- Error states (helpful or generic messages?)
- Loading states (indicators for async operations, or UI freezes?)
- Empty states (helpful or confusing with no data?)
- Mobile UX (good on mobile or just squeezed desktop? touch targets adequate?)
- Onboarding (smooth setup/registration flow?)
- Dead ends & confusion points (moments where user thinks "now what?")

#### Step 6: Performance Lens Rubric
- Core Web Vitals (LCP, INP, CLS — green/yellow/red)
- Total page weight
- Image optimization (modern formats? properly sized? lazy loading?)
- JavaScript bundle size (dead code? oversized deps?)
- Render-blocking resources
- Cache headers
- Network waterfall bottlenecks

#### Step 7: Accessibility Lens Rubric
- Color contrast (WCAG AA: 4.5:1 normal text, 3:1 large text)
- Alt text (all meaningful images? decorative images marked?)
- Keyboard navigation (all interactive elements reachable? logical focus order? visible focus styles?)
- Semantic HTML (proper heading hierarchy? landmarks: nav, main, footer? lists as lists?)
- ARIA usage (correct or misapplied? bad ARIA is worse than none)
- Form labels (all inputs labeled? required fields indicated?)
- Screen reader experience (makes sense linearly? dynamic changes announced?)
- Motion/animation (prefers-reduced-motion? excessive animations?)

#### Step 8: Code Quality & Content Lens Rubric

Code:
- Semantic HTML (div-soup vs. proper semantics)
- Meta tags & SEO (title, description, OG, canonical, structured data)
- Responsive implementation (proper techniques or hidden overflow?)
- Console cleanliness (console.logs left in? warning spam?)
- Resource loading (defer/async? font loading strategy?)

Content:
- Placeholder content ("Lorem ipsum", "TODO", "asdf")
- Spelling & grammar (typos, inconsistent capitalization)
- Tone consistency (one voice or patchwork?)
- Missing content (empty sections, broken images, "coming soon")
- Microcopy (button labels, error messages, helper text — clear and useful?)

### Step 9: Synthesis & Scoring (LLM — Gemini Pro)

**Module:** `scanner/synthesis.py`

**Inputs:** All findings from Steps 3–8 + intent analysis

**Actions:**
1. **Deduplicate:** Same root issue surfacing in multiple lenses → merge into single finding with multiple lens tags
2. **Identify systemic patterns:** "The app generally lacks loading states" > 5 separate findings
3. **Priority rank:** severity × impact × effort. Critical + quick_fix > medium + significant
4. **Score each lens:** 0–100 based on findings count and severity distribution
5. **Score overall:** Weighted composite
6. **Determine verdict:**
   - **GO:** No critical findings. May have high/medium/low findings but nothing blocking.
   - **NO-GO:** Any critical finding = automatic NO-GO. Or 3+ high findings in core flow.
   - **GO WITH CONDITIONS:** No critical, but high findings that should be addressed within defined timeframe.
7. **Select top 3 actions:** Highest impact fixes across all lenses

**Output:** Synthesis JSON (see data model above)

### Step 10: Dual Report Generation (LLM — Gemini Pro)

**Module:** `scanner/report_gen.py`

**Inputs:** Synthesis output + all findings + all screenshots

**Generates two markdown files:**

#### Report A (AI Handoff) — `report_a.md`

Structure:
```markdown
# GoNoGo Report — [Project Name/URL]
## Verdict: [GO | NO-GO | GO WITH CONDITIONS]
## Overall Score: [score]/100 ([grade])
## Tech Stack: [detected stack]
## Scan Date: [date]

### Critical (fix before launch)
#### [ID]: [title]
- Page: [url]
- Selector: [css selector]
- Issue: [precise technical description]
- Fix: [exact actionable instruction]
- File hint: [likely file path based on tech stack]

### High Priority
...

### Medium Priority
...

### Low Priority
...
```

Design principles:
- Every finding = discrete, actionable instruction
- Include selectors, file path hints, code suggestions
- A coding AI must be able to act on every item without asking for clarification
- Zero conversational tone — pure signal, maximum density

#### Report B (Human Review) — `report_b.md`

Structure:
```markdown
# GoNoGo Report — [Project Name/URL]
## [VERDICT BADGE] — [score]/100 ([grade])

### Executive Summary
[One paragraph. Opinionated. Direct. What's the overall picture?]

### What's Working Well
[Specific praise with evidence. Not generic — "Your product photography is consistently high-quality and well-lit" not "The images are nice."]

### Critical Issues
[Each with annotated screenshot reference, explanation of WHY it matters, and HOW to fix it]

### Improvements
[Ranked by impact. Each explains the user impact.]

### Polish Suggestions
[Nice-to-haves that elevate "works" to "professional"]

### Score Breakdown
[Per-lens scores with one-line summaries]

### Top 3 Actions
[If you only fix three things, fix these]
```

Design principles:
- Lead with big picture
- Annotated screenshot references for visual findings
- Explain WHY things matter, not just WHAT is wrong
- Opinionated, direct tone — like a reliable senior colleague
- "This checkout flow will lose you customers" not "Suboptimal conversion pathway detected"
- Encouraging — acknowledges good work, treats builder as a peer

---

## 9. PROMPT TEMPLATES

### Prompt Engineering Principles (Apply to ALL prompts)

1. **Structured output always.** Request JSON. Parse and validate every response.
2. **Rubric-driven.** Specific criteria, not vague asks. Ground evaluation in observable evidence.
3. **Evidence-required.** Every finding must reference a screenshot, DOM element, console error, or URL. No evidence = discard the finding.
4. **Dual recommendations.** Every finding must produce both `human_readable` and `ai_actionable` recommendation strings.
5. **Persona injection.** Each lens uses a specific persona (see below).
6. **Calibration examples.** Each prompt includes 1–2 examples of GOOD vs BAD findings.
7. **Confidence scoring.** Each finding includes confidence 0.0–1.0. Low confidence = "potential issue" in Report B.
8. **Self-review.** After generating findings, the prompt instructs the LLM to review its own output against the evidence and prune anything that doesn't hold up.

### Persona Per Lens
- Functionality: "You are a senior QA engineer doing a pre-launch audit."
- Design: "You are a senior product designer reviewing this for a portfolio critique."
- UX: "You are a first-time user who has never seen this app before."
- Performance: "You are a web performance consultant."
- Accessibility: "You are an accessibility specialist evaluating WCAG 2.1 AA compliance."
- Code/Content: "You are a senior frontend developer doing a code review."

### Calibration Example (Include in every lens prompt)

```
EXAMPLE OF A BAD FINDING:
{
  "title": "The colors are off",
  "description": "Some colors don't look right.",
  "evidence": {},
  "recommendation": {"human_readable": "Fix the colors", "ai_actionable": "Change colors"}
}

EXAMPLE OF A GOOD FINDING:
{
  "title": "CTA button invisible against hero background",
  "description": "The primary CTA button (#4A90D2) on the hero section sits against a similar-toned background (#3B7DD8), creating a contrast ratio of only 1.3:1. The button is nearly invisible.",
  "evidence": {
    "page_url": "/",
    "screenshot_ref": "homepage_desktop.png",
    "dom_selector": "section.hero button.cta-primary"
  },
  "recommendation": {
    "human_readable": "Your main call-to-action is practically invisible. Change the button to a contrasting color like white (#FFFFFF) or dark (#1A1A2E) so it pops against the blue hero.",
    "ai_actionable": "In the hero section, change .cta-primary background-color from #4A90D2 to #FFFFFF with color: #1A1A2E. This achieves a contrast ratio of 15.4:1."
  }
}
```

### Report B Tone Guidance (Include in Report Generation prompt)

```
TONE: You are an opinionated, direct senior colleague. You sincerely want this person to succeed.

DO:
- Say exactly what you think: "This checkout flow will lose you customers."
- Give specific, actionable praise: "Your product copy is warm and authentic — it sounds like a real person, not a brand."
- Explain WHY: "This matters because first-time visitors decide within 5 seconds whether to stay."
- Be constructive: every criticism comes with a specific fix.

DON'T:
- Hedge: "This might perhaps be slightly suboptimal..."
- Be generic: "The design could use some work."
- Be cruel: "This looks terrible."
- Use corporate speak: "Suboptimal conversion pathway detected."
```

### Prompt Template File Format

Each prompt template in `/prompts/` follows this format:

```markdown
# [Lens Name] Evaluation Prompt — v[N]
# Model: [gemini-2.5-pro | gemini-2.5-flash]
# Last updated: [date]

## System

[persona injection]

You are evaluating a web application. Your job is to [specific task].

## Context

Project intent: {{intent_analysis_json}}
Tech stack: {{tech_stack_json}}

## Evidence

{{relevant_recon_data}}

## Screenshots

{{screenshot_descriptions_or_references}}

## Rubric

Evaluate against each of these criteria:
[specific rubric items]

## Output Format

Respond with a JSON array of findings. Each finding must follow this exact schema:
[Finding schema]

## Calibration

[GOOD vs BAD finding examples]

## Self-Review

Before finalizing, review each finding:
- Does it reference specific evidence? If not, remove it.
- Is the recommendation actionable? If vague, make it specific.
- Could a coding AI act on the ai_actionable recommendation without asking questions? If not, rewrite it.
```

---

## 10. REPORT GENERATION

### Report A Template

The AI-consumable report follows a strict, predictable structure for machine parsing:

```markdown
# GoNoGo Report A — AI Handoff
# URL: {{url}}
# Verdict: {{verdict}}
# Score: {{overall_score}}/100 ({{overall_grade}})
# Tech Stack: {{tech_stack_summary}}
# Scanned: {{date}}
# Prompt Versions: {{prompt_versions_json}}

---

## CRITICAL — Fix Before Launch
{{#each critical_findings}}
### {{id}}: {{title}}
- **Page:** {{evidence.page_url}}
- **Selector:** {{evidence.dom_selector}}
- **Issue:** {{description}}
- **Console:** {{evidence.console_errors}}
- **Network:** {{evidence.network_evidence}}
- **Fix:** {{recommendation.ai_actionable}}
- **File hint:** {{file_path_hint}}
{{/each}}

## HIGH PRIORITY
{{#each high_findings}}
[same structure]
{{/each}}

## MEDIUM PRIORITY
{{#each medium_findings}}
[same structure]
{{/each}}

## LOW PRIORITY
{{#each low_findings}}
[same structure]
{{/each}}
```

### Report B Template

The human-readable report uses rich markdown with personality:

```markdown
# GoNoGo Report — {{project_name}}
## {{verdict_emoji}} {{verdict}} — {{overall_score}}/100 ({{overall_grade}})

---

### Executive Summary
{{executive_summary}}

---

### What's Working Well
{{positives_section}}

---

### Critical Issues
{{#each critical_findings}}
#### {{title}}
![{{screenshot_alt}}]({{screenshot_ref}})
{{human_readable_description}}
**Why this matters:** {{impact_explanation}}
**How to fix it:** {{recommendation.human_readable}}
{{/each}}

---

### Improvements
{{#each high_and_medium_findings}}
#### {{title}}
{{human_readable_description}}
**Fix:** {{recommendation.human_readable}}
*Effort: {{effort}} | Category: {{lens}}*
{{/each}}

---

### Polish Suggestions
{{#each low_findings}}
- **{{title}}:** {{recommendation.human_readable}}
{{/each}}

---

### Score Breakdown

| Lens | Score | Grade | Summary |
|------|-------|-------|---------|
{{#each lens_scores}}
| {{lens}} | {{score}}/100 | {{grade}} | {{summary}} |
{{/each}}

---

### If You Only Fix Three Things
1. {{top_3_actions[0]}}
2. {{top_3_actions[1]}}
3. {{top_3_actions[2]}}
```

---

## 11. CONFIGURATION & ENVIRONMENT

### `.env.example`

```env
# Required
GEMINI_API_KEY=your_gemini_api_key_here

# Optional (secondary LLM)
ANTHROPIC_API_KEY=your_claude_api_key_here

# LLM defaults
DEFAULT_LLM_PROVIDER=gemini
GEMINI_PRO_MODEL=gemini-2.5-pro
GEMINI_FLASH_MODEL=gemini-2.5-flash
CLAUDE_MODEL=claude-sonnet-4-5-20250929

# Storage
STORAGE_DIR=./storage
DATABASE_URL=sqlite:///./data/gonogo.db

# Server
BACKEND_PORT=8000
FRONTEND_PORT=5173
CORS_ORIGINS=http://localhost:5173

# Scan limits
MAX_DEEP_PAGES=30
MAX_SHALLOW_PAGES=100
MAX_SCAN_DURATION_SECONDS=600
MAX_UPLOAD_SIZE_MB=10
```

### Backend Requirements (`requirements.txt`)

```
fastapi>=0.100.0
uvicorn>=0.23.0
sqlalchemy>=2.0.0
pydantic>=2.0.0
playwright>=1.40.0
google-generativeai>=0.5.0
anthropic>=0.25.0
python-multipart>=0.0.6
sse-starlette>=1.6.0
aiofiles>=23.0.0
Pillow>=10.0.0
httpx>=0.25.0
python-dotenv>=1.0.0
```

### Frontend Dependencies

```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.20.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.0",
    "@vitejs/plugin-react": "^4.2.0",
    "typescript": "^5.3.0",
    "vite": "^5.0.0"
  }
}
```

---

## 12. DEPLOYMENT

### V1 (Personal Use)

**Frontend:**
- GitHub → Vercel (auto-deploy on push)
- Free tier is sufficient
- Set environment variable: `VITE_API_URL` pointing to backend

**Backend:**
- Railway (easiest) or VPS (cheapest)
- Railway: connect GitHub repo, set environment variables, deploy
- VPS: any $5–12/mo provider (Hetzner, DigitalOcean). Run with systemd + nginx.
- MUST support persistent processes (for Playwright browser sessions lasting 2–5 min)
- Install Playwright browsers: `playwright install chromium`
- Install Lighthouse: `npm install -g lighthouse`

### Production Checklist
- [ ] HTTPS on both frontend and backend
- [ ] CORS configured correctly
- [ ] API key never logged or stored beyond the request
- [ ] Uploaded files cleaned up after scan completion (or after configurable retention period)
- [ ] Rate limiting on scan creation (prevent abuse)
- [ ] Error handling: scan timeout, LLM API failures, Playwright crashes → graceful error state

---

## 13. STRATEGIC CONTEXT

### This Tool Is Part of BaryApps

BaryApps is a central hub/repository (like a "desktop") that lists a collection of independently-deployed tools. GoNoGo lives at its own URL as a standalone web app, but is listed on BaryApps. It does NOT need to share infrastructure with other BaryApps tools for V1. Shared auth/billing comes later.

### Business Model

- **V1:** BYOK only. User provides their own Gemini API key. No cost to the founder beyond hosting (~$5–20/mo).
- **Future:** BYOK tier (free) + hosted tier ($2–5/scan) + subscription ($19–79/mo). Target users: vibe coders, solo developers, students.

### Cost Per Scan: ~$0.50

| Step | Model | Est. Cost |
|------|-------|-----------|
| Step 0: Recon | None | $0.00 |
| Step 1: Intent | Pro | $0.013 |
| Step 2: Tech Stack | Flash | $0.002 |
| Step 3: Functionality | Flash | $0.012 |
| Step 4: Design | Pro | $0.063 |
| Step 5: UX | Pro | $0.047 |
| Step 6: Performance | Flash | $0.008 |
| Step 7: Accessibility | Flash | $0.008 |
| Step 8: Code/Content | Flash | $0.011 |
| Step 9: Synthesis | Pro | $0.052 |
| Step 10: Reports | Pro | $0.127 |
| **Total (with buffer)** | | **~$0.50** |

### Agent Personality

Report B tone: Opinionated and direct. Like a reliable, competent senior who sincerely wants you to be better. Says exactly what's on its mind. Direct but not cruel. Acknowledges good work. Explains WHY things matter. Talks like a person, not a tool.

Report A tone: No personality. Pure structured data.

### V1 Definition of Done (Repeated for Emphasis)

Pick an existing BaryApps tool → run GoNoGo → take Report A → paste it into Claude Code → the coding AI understands every finding and can act on it without asking for clarification → the fixes are actually correct and useful. **If that works, V1 ships.**

---

## 14. FIX LOOP INTEGRATION

### Overview

GoNoGo includes an **automated fix loop** that feeds Report A directly to Claude Code in headless mode, monitors fix progress, triggers rebuilds/redeploys, rescans the fixed version, and iterates until the verdict reaches GO or the cycle limit is reached.

### Prerequisites

Before using the fix loop:

1. **Claude Code installed** — The CLI must be available on the system path
2. **Git repository** — The target project must be a git repository
3. **Deploy pipeline configured** — User must specify how to rebuild/redeploy (or use local dev server)
4. **Token budget** — User must set a Claude Code token budget per cycle

### Architecture

```
[GoNoGo Scan] → Report A Generated
       ↓
[Fix Loop Orchestrator]
       ↓
┌──────────────────────────────────────────┐
│ CYCLE N (max 3 by default, configurable) │
│                                          │
│ 1. Feed Report A to Claude Code          │
│    (headless mode, file input)           │
│                                          │
│ 2. Monitor progress via Claude Code API  │
│    (permissions, budget, tool usage)     │
│                                          │
│ 3. Trigger rebuild/redeploy              │
│    (branch-based preview deploy default) │
│                                          │
│ 4. Wait for deployment ready             │
│                                          │
│ 5. Rescan deployed version               │
│    (full GoNoGo pipeline)                │
│                                          │
│ 6. Generate delta report                 │
│    (what fixed, what regressed, new)     │
│                                          │
│ 7. Check verdict                         │
│    → GO: Stop, success                   │
│    → NO-GO/CONDITIONS: Next cycle        │
└──────────────────────────────────────────┘
```

### Claude Code Headless Integration

**Invocation Method:**

Report A is fed to Claude Code via **file input** (not stdin), allowing Claude Code to parse the full structured markdown with proper formatting.

```bash
claude-code --headless \
  --file report_a.md \
  --budget 100000 \
  --permissions "edit,write,bash:git*,bash:npm*" \
  --workspace /path/to/project
```

**Configuration:**

| Parameter | Default | Notes |
|-----------|---------|-------|
| `--budget` | 100,000 tokens | Configurable per cycle. If exceeded, cycle stops with partial fixes. |
| `--permissions` | Configured at scan time | User reviews allowed tools before starting loop. |
| `--timeout` | 30 minutes | Max duration per fix cycle. |
| `--allowed-tools` | Edit, Write, Bash (limited), Read, Grep, Glob | No Task, no ExitPlanMode. |
| `--allowed-bash` | Git operations, build commands (user-configured) | No destructive operations (rm -rf, force push, etc.) unless explicitly allowed. |

**Allowed Tools:**

- **Edit, Write, Read** — Core file operations
- **Grep, Glob** — Code search
- **Bash** — Limited to git operations and build commands (user-configured whitelist)
- **NOT allowed** — Task (no subagents), ExitPlanMode, WebFetch, WebSearch

**Permissions Model:**

User reviews and approves the following before fix loop starts:
1. Which bash commands Claude Code can run (git add/commit, npm build, etc.)
2. Token budget per cycle
3. Whether Claude Code can create new files (default: yes for fix implementations)
4. Whether Claude Code can modify existing files (default: yes)

**Budget Management:**

- If Claude Code exhausts the token budget mid-cycle, the cycle stops
- Partial fixes are committed to the git branch
- User can review progress and manually continue or adjust budget for next cycle

### Git Branch Strategy

**Default Behavior:**

All fixes are made on a dedicated branch: `gonogo/fix-<scan_id>`

**Workflow:**

1. Before fix loop starts, create branch from current HEAD
2. All Claude Code edits happen on this branch
3. Each fix cycle commits changes with descriptive messages
4. After all cycles complete (or user stops), user can:
   - Review the branch diff
   - Merge to main via PR
   - Discard the branch

**Direct Edit Option:**

User can opt-in to direct edits on current branch (bypassing gonogo/fix-* branch creation). Must be explicitly chosen at scan time.

**Safety:**

- Never force push
- Never modify git config
- Never run destructive git commands (reset --hard, clean -f, etc.) without explicit user permission
- All commits include scan_id in message for traceability

### Deploy Pipeline Configuration

**Three Deployment Modes:**

| Mode | When to Use | How It Works |
|------|-------------|--------------|
| **Branch-based preview deploy** (default) | Vercel, Netlify, Railway with branch deploys | Push to `gonogo/fix-<scan_id>` → wait for preview URL → rescan preview |
| **Manual rebuild** | Local projects, non-automated deploys | Run user-configured build command → rescan localhost |
| **Local dev server rescan** | Fast iteration, no rebuild needed | Rescan existing dev server (assumes hot reload) |

**User Configuration (at scan time):**

```json
{
  "deploy_mode": "branch_preview",
  "deploy_command": "git push origin gonogo/fix-{scan_id}",
  "preview_url_pattern": "https://gonogo-fix-{scan_id}.vercel.app",
  "wait_for_deploy": true,
  "deploy_timeout_seconds": 300
}
```

**Manual Rebuild Example:**

```json
{
  "deploy_mode": "manual_rebuild",
  "build_command": "npm run build && npm run preview",
  "rescan_url": "http://localhost:4173"
}
```

**Local Dev Server Example:**

```json
{
  "deploy_mode": "dev_server",
  "rescan_url": "http://localhost:5173"
}
```

### Cycle Configuration

**Default Settings:**

- **Max cycles:** 3
- **Stop conditions:**
  - Verdict = GO
  - Max cycles reached
  - Claude Code budget exhausted
  - User manually stops
  - Critical error (deployment failed, rescan failed, etc.)

**User-Configurable:**

```json
{
  "max_cycles": 3,
  "stop_on_verdict": "GO",
  "continue_on_conditions": false,
  "budget_per_cycle": 100000,
  "allow_partial_fixes": true
}
```

**Behavior:**

- **Cycle 1:** Full Report A fed to Claude Code
- **Cycle 2+:** Delta report fed (what remains unfixed + what regressed)
- Each cycle commits fixes with message: `gonogo fix cycle N: <summary>`

### Delta Reporting (Cycle 2+)

**Purpose:** After Cycle 1, subsequent cycles receive a **delta report** instead of the full Report A.

**Delta Report Sections:**

```markdown
# GoNoGo Delta Report — Cycle N
# Previous Score: 72/100 (C+) → Current Score: 78/100 (B-)
# Verdict: NO-GO → GO WITH CONDITIONS

## Fixed Since Last Cycle
- [FUNC-001] Checkout form submission bug → RESOLVED
- [A11Y-003] Product image alt text → RESOLVED (42/43 fixed)

## Remaining Issues
- [PERF-002] Hero image size (2.4MB) → UNFIXED
- [DESIGN-005] Inconsistent button padding → UNFIXED

## New Issues Detected
- [FUNC-007] Form validation broken by Cycle 1 fix → NEW CRITICAL

## Regressions
- [UX-004] Mobile nav previously working, now broken → REGRESSION

## Priority Actions for This Cycle
1. Fix FUNC-007 (new critical introduced in last cycle)
2. Investigate UX-004 regression
3. Address PERF-002 (hero image optimization)
```

**Why Delta Reporting:**

- Avoids re-fixing already-resolved issues
- Highlights regressions (fixes that broke something else)
- Focuses Claude Code's attention on remaining work
- Tracks fix velocity across cycles

**Report Naturally Deprioritizes:**

As critical issues are resolved, the remaining issues naturally rise in priority. No explicit severity escalation needed per cycle — the delta report's "Priority Actions" section handles this.

### New API Endpoints

#### POST `/api/scans/{scan_id}/fix-loop/start`

**Purpose:** Start the automated fix loop for a completed scan.

**Request Body:**

```json
{
  "deploy_config": {
    "mode": "branch_preview",
    "deploy_command": "git push origin gonogo/fix-{scan_id}",
    "preview_url_pattern": "https://gonogo-fix-{scan_id}.vercel.app",
    "wait_for_deploy": true,
    "deploy_timeout_seconds": 300
  },
  "cycle_config": {
    "max_cycles": 3,
    "stop_on_verdict": "GO",
    "budget_per_cycle": 100000
  },
  "claude_code_config": {
    "allowed_bash_commands": ["git add", "git commit", "npm run build", "npm run preview"],
    "allowed_tools": ["Edit", "Write", "Read", "Grep", "Glob", "Bash"],
    "workspace_path": "/path/to/project"
  },
  "git_config": {
    "use_branch": true,
    "branch_name": "gonogo/fix-{scan_id}",
    "allow_direct_edits": false
  }
}
```

**Response:**

```json
{
  "fix_loop_id": "fixloop_uuid",
  "status": "running",
  "current_cycle": 1,
  "max_cycles": 3
}
```

#### GET `/api/scans/{scan_id}/fix-loop/{fix_loop_id}`

**Purpose:** Get fix loop status and progress.

**Response:**

```json
{
  "fix_loop_id": "fixloop_uuid",
  "status": "running",
  "current_cycle": 2,
  "max_cycles": 3,
  "cycles": [
    {
      "cycle_number": 1,
      "status": "completed",
      "tokens_used": 87340,
      "fixes_applied": 12,
      "verdict_after": "GO WITH CONDITIONS",
      "score_after": 78
    },
    {
      "cycle_number": 2,
      "status": "running",
      "tokens_used": 45200,
      "current_step": "claude_code_fixing"
    }
  ]
}
```

#### GET `/api/scans/{scan_id}/fix-loop/{fix_loop_id}/stream`

**Purpose:** SSE stream of fix loop progress.

**Events:**

```
event: cycle_start
data: {"cycle": 2, "message": "Starting fix cycle 2 of 3"}

event: claude_code_progress
data: {"message": "Editing app/checkout/page.tsx", "tokens_used": 12340}

event: deploy_start
data: {"message": "Pushing to branch gonogo/fix-abc123"}

event: rescan_start
data: {"message": "Rescanning deployed version"}

event: cycle_complete
data: {"cycle": 2, "verdict": "GO", "score": 85, "message": "Verdict reached GO, stopping loop"}

event: loop_complete
data: {"total_cycles": 2, "final_verdict": "GO", "final_score": 85}
```

#### POST `/api/scans/{scan_id}/fix-loop/{fix_loop_id}/stop`

**Purpose:** Manually stop the fix loop.

**Response:**

```json
{
  "message": "Fix loop stopped after cycle 2",
  "final_verdict": "GO WITH CONDITIONS",
  "final_score": 78
}
```

#### GET `/api/scans/{scan_id}/fix-loop/{fix_loop_id}/delta/{cycle_number}`

**Purpose:** Download delta report for a specific cycle.

**Response:** Markdown file download.

### New Data Models

#### FixLoop Model

```python
class FixLoop(Base):
    __tablename__ = "fix_loops"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    scan_id = Column(String, ForeignKey("scans.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Configuration
    deploy_config = Column(JSON, nullable=False)
    cycle_config = Column(JSON, nullable=False)
    claude_code_config = Column(JSON, nullable=False)
    git_config = Column(JSON, nullable=False)

    # Status
    status = Column(String, default="pending")  # pending | running | completed | failed | stopped
    current_cycle = Column(Integer, default=0)
    max_cycles = Column(Integer, nullable=False)

    # Results
    final_verdict = Column(String, nullable=True)
    final_score = Column(Integer, nullable=True)
    total_tokens_used = Column(Integer, default=0)
    total_fixes_applied = Column(Integer, default=0)
```

#### FixCycle Model

```python
class FixCycle(Base):
    __tablename__ = "fix_cycles"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    fix_loop_id = Column(String, ForeignKey("fix_loops.id"), nullable=False)
    cycle_number = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Status
    status = Column(String, default="pending")  # pending | running | completed | failed
    current_step = Column(String, nullable=True)

    # Claude Code execution
    claude_code_session_id = Column(String, nullable=True)
    tokens_used = Column(Integer, default=0)
    budget_exhausted = Column(Boolean, default=False)

    # Fixes
    fixes_applied = Column(Integer, default=0)
    files_modified = Column(JSON, nullable=True)  # List of file paths
    git_commits = Column(JSON, nullable=True)     # List of commit SHAs

    # Rescan results
    rescan_id = Column(String, nullable=True)
    verdict_after = Column(String, nullable=True)
    score_after = Column(Integer, nullable=True)
    score_delta = Column(Integer, nullable=True)  # Change from previous cycle

    # Delta report
    delta_report_path = Column(String, nullable=True)
    fixed_issues = Column(JSON, nullable=True)
    remaining_issues = Column(JSON, nullable=True)
    new_issues = Column(JSON, nullable=True)
    regressions = Column(JSON, nullable=True)
```

### New Config Schema

Add to `.env.example`:

```env
# Fix Loop Configuration
CLAUDE_CODE_PATH=claude-code
CLAUDE_CODE_DEFAULT_BUDGET=100000
CLAUDE_CODE_MAX_TIMEOUT_SECONDS=1800
FIX_LOOP_MAX_CYCLES=3
FIX_LOOP_DEFAULT_DEPLOY_TIMEOUT=300
```

### Implementation Notes

**Error Handling:**

- If Claude Code crashes mid-cycle, save partial progress, mark cycle as failed, allow user to resume or retry
- If deployment fails, mark cycle as failed, provide error details, allow manual intervention
- If rescan fails, retry once, then mark cycle as failed

**Safety:**

- All git operations logged and traceable
- All Claude Code permissions explicitly approved by user before loop starts
- Token budget prevents runaway costs
- Deploy timeout prevents infinite waits
- Max cycles prevents infinite loops

**Performance:**

- Claude Code runs in headless mode (no UI overhead)
- Rescans reuse existing Playwright browser instance if possible
- Delta reports are lightweight (only changed findings)

**User Experience:**

- Clear progress indicators via SSE stream
- Ability to pause/resume fix loop
- Downloadable delta reports for each cycle
- Git branch diffs reviewable at any time

### Build Order Impact

**New Phase: Fix Loop (Phase 10):**

Build this after Phase 9 (polish & hardening):

1. Implement `claude_code_runner.py` — headless invocation with permission sandboxing
2. Implement `fix_orchestrator.py` — cycle management, delta generation
3. Implement `deploy_pipeline.py` — rebuild/redeploy coordination for all three modes
4. Wire up new API endpoints for fix loop control
5. Add FixLoop and FixCycle models to database
6. Build frontend UI for fix loop configuration and progress monitoring
7. Test end-to-end: scan → fix loop → branch preview → rescan → delta → cycle 2 → GO verdict

---

*End of specification. Build it.*
