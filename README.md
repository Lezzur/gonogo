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

## Cost Per Scan

Approximately $0.50 using Gemini API (with BYOK model).

## Tech Stack

- **Frontend**: React + Vite + TypeScript + Tailwind CSS
- **Backend**: Python + FastAPI
- **Browser Automation**: Playwright
- **Performance**: Lighthouse CLI
- **Accessibility**: axe-core
- **LLM**: Gemini 2.5 Pro/Flash (primary), Claude (secondary)
- **Database**: SQLite (V1)

## License

Proprietary - Part of BaryApps tool suite.
