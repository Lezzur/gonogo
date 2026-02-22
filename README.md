# GoNoGo

AI-powered QA and design evaluation agent. Get a **GO / NO-GO / GO WITH CONDITIONS** verdict before you ship.

## What GoNoGo Does

Submit a URL (plus optional context), and an AI agent autonomously:
- Crawls and screenshots your site
- Runs Lighthouse and axe-core audits
- Evaluates across 7 quality lenses
- Produces two downloadable reports:
  - **Report A (AI Handoff)**: Machine-parseable markdown for coding AIs
  - **Report B (Human Review)**: Rich, visual report with explanations

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- A Gemini API key (or Claude API key)

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium

# Copy environment file
copy ..\.env.example .env
# Edit .env with your settings

# Run the server
python main.py
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Run dev server
npm run dev
```

### Install Lighthouse (optional but recommended)

```bash
npm install -g lighthouse
```

## Usage

1. Open http://localhost:5173
2. Enter the URL you want to scan
3. Enter your Gemini or Claude API key
4. Click "Run GoNoGo"
5. Wait 2-5 minutes for the scan to complete
6. Download your reports

## Architecture

```
[React Frontend]
      │
      │ REST API + SSE
      ▼
[FastAPI Backend]
      │
      ▼
[Background Scan Worker]
      │
      ├── Step 0: Playwright + Lighthouse + axe-core
      ├── Step 1-2: Intent & Tech Stack Analysis
      ├── Steps 3-8: 6 Lens Evaluations (parallel)
      ├── Step 9: Synthesis & Scoring
      └── Step 10: Dual Report Generation
```

## The 7 Quality Lenses

1. **Functionality** - JS errors, broken links, forms, interactive elements
2. **Design** - Color, typography, spacing, visual hierarchy, polish
3. **UX** - Navigation, CTAs, loading states, mobile experience
4. **Performance** - Core Web Vitals, page weight, optimization
5. **Accessibility** - WCAG 2.1 AA compliance, axe-core violations
6. **Code Quality** - Semantic HTML, SEO, console cleanliness
7. **Content** - Placeholder text, typos, microcopy

## Automated Fix Loop

GoNoGo can automatically feed Report A to Claude Code in headless mode, apply fixes, rebuild/redeploy, and rescan — iterating until the verdict reaches GO or the cycle limit is reached.

### Prerequisites

Before using the automated fix loop:

1. **Claude Code installed** — The CLI must be available on your system
2. **Git repository** — Your project must be a git repository
3. **Deploy pipeline** — Configure how to rebuild/redeploy (or use local dev server)

### How It Works

1. Complete a GoNoGo scan and get your reports
2. Click "Start Fix Loop" and configure:
   - Deploy method (branch preview, manual rebuild, or dev server)
   - Claude Code permissions and token budget
   - Max fix cycles (default: 3)
3. GoNoGo creates a git branch (`gonogo/fix-<scan_id>`) for safety
4. Report A is fed to Claude Code in headless mode
5. Claude Code applies fixes within configured permissions
6. Changes are committed to the fix branch
7. Your app is rebuilt/redeployed (based on your config)
8. GoNoGo rescans the fixed version
9. A delta report shows what fixed, what regressed, and what's new
10. Process repeats until GO verdict or max cycles reached

### Usage Flow

```bash
# 1. Run initial scan
Open GoNoGo UI → Enter URL → Run scan → Download reports

# 2. Start fix loop (via UI)
Review Report A → Configure fix loop settings → Start loop

# 3. Monitor progress
Watch SSE stream showing:
  - Claude Code applying fixes
  - Git commits being created
  - Deployment progress
  - Rescan results
  - Delta report generation

# 4. Review results
After loop completes:
  - Review git branch diff: git diff main..gonogo/fix-<scan_id>
  - Download delta reports for each cycle
  - Merge fix branch via PR if satisfied
```

### Git Branch Safety

All fixes are made on a dedicated branch by default:
- Branch name: `gonogo/fix-<scan_id>`
- You can review all changes before merging
- Original code remains untouched on main branch
- Can discard the fix branch if results aren't satisfactory

**Direct edit option:** You can opt-in to direct edits on your current branch, but this must be explicitly chosen at scan time.

## Cost Per Scan

Approximately $0.50 using Gemini API (with BYOK model).

## Tech Stack

- **Frontend**: React + Vite + TypeScript + Tailwind CSS
- **Backend**: Python + FastAPI
- **Browser Automation**: Playwright
- **Performance**: Lighthouse CLI
- **Accessibility**: axe-core
- **LLM**: Gemini 3 Pro/Flash Preview (primary), Claude (secondary)
- **Database**: SQLite (V1)

## License

Proprietary - Part of BaryApps tool suite.
