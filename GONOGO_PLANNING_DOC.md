# Project Blueprint: GoNoGo — AI QA & Design Evaluation Agent

> **Status:** Planning & Discovery Phase
> **Last Updated:** February 13, 2026
> **Document Type:** Living Document — updated as the project evolves

---

## 1. Project Vision

An AI-powered testing agent that can autonomously navigate a web app (or website/tool), understand the creator's intent, evaluate the project across multiple dimensions, identify errors and design flaws, and deliver actionable improvement suggestions — functioning as an automated QA engineer, design critic, and product advisor in one.

### Why This Exists

AI-assisted development ("vibe coding") has made it easy to build and ship fast, but quality assurance, design review, and UX evaluation still require manual effort or expensive human reviewers. This tool closes that gap — giving solo developers, students, and vibe coders a tireless, opinionated tester that works as hard as they do.

---

## 2. Core Agent Loop

The agent operates in four sequential phases:

### Phase 1: Understand Intent

The agent gathers context through a combination of user-provided input and autonomous inference.

**User Input Interface (3 input channels + 1 optional field):**

1. **Text Field** — Free-form area where the user provides details, information, and/or specific instructions about the project. Could be a one-liner ("e-commerce store for handmade candles") or a detailed brief with target audience, goals, and key flows.
2. **File Upload Box** — Drag/drop and paste support for any visual reference material: sketches, wireframes, mockups, reference designs, handwritten notes, spec documents, screenshots of desired functionality, or any image that helps communicate intent. Not limited to design — could include technical specs, feature lists, or annotated screenshots.
3. **URL Input** — The target URL to evaluate.
4. **Tech Stack Field (optional)** — User can specify the tech stack if known (e.g., "Next.js, Tailwind, Supabase"). Clearly labeled as optional. Helps the AI-consumable report (Report A) reference correct file paths, component structures, and framework-specific patterns.

**Autonomous Context Gathering:**
- The agent should be smart enough to supplement user-provided input by independently gathering information from the URL, the website, its content, the app itself, and any other available sources
- Read landing page copy, meta tags, sitemap, README if accessible
- Infer project type, target audience, and purpose from the app itself
- **Infer tech stack** from script tags, framework signatures, meta generators, CDN references, HTTP headers, and DOM patterns — cross-reference with user-provided tech stack if given
- Cross-reference user-provided sketches/mockups against the live app to identify gaps between intent and execution

**Design Principle:** The more context the user gives, the sharper the evaluation — but the agent should deliver a valuable assessment even with just a URL.

### Phase 2: Explore & Observe
- Navigate the app like a real user — crawl pages, click buttons, fill forms, test navigation paths
- Capture screenshots, console output, network requests, load times
- Identify and prioritize user journeys based on inferred project goals
- Smart exploration: if it's an e-commerce site, prioritize search → product → cart → checkout over about page typos
- **User-Specified Test Routes:** The user can optionally define a specific route/flow for the agent to follow (e.g., "test the checkout flow" or "focus on the onboarding sequence"). If no route is specified, the agent explores autonomously based on inferred priorities.

### Phase 3: Evaluate Across Multiple Lenses

| Lens | What It Checks |
|------|---------------|
| **Functionality** | Broken links, form submission, console errors, broken images, 404s, dead ends, JS errors |
| **Design Quality** | Visual consistency, spacing, hierarchy, contrast, professional polish vs. template feel |
| **UX Flow** | Discoverability, happy path clarity, confusing dead ends, unclear CTAs, onboarding friction |
| **Performance** | Load times, image optimization, render-blocking resources, Core Web Vitals |
| **Accessibility** | Color contrast (WCAG), alt text, keyboard navigation, screen reader compatibility, ARIA usage |
| **Code Quality** | Semantic HTML, responsive implementation, SEO basics, clean markup |
| **Copy & Content** | Typos, tone consistency, placeholder text ("Lorem ipsum"), missing meta descriptions |

### Phase 4: Report & Recommend
- Generates **two separate reports** from the same evaluation findings (see Section 6: Output Strategy)
- **Report A (AI Handoff):** Structured, precise, machine-parseable markdown with file paths and selectors — designed to be pasted directly into a coding AI
- **Report B (Human Review):** Contextual, visual, explanatory — written for the developer to read, understand, and prioritize
- Prioritized, actionable suggestions — not just problem identification
- Specific fixes with examples (e.g., "bump button color to #1a6b3f for AA compliance")

---

## 3. Report Structure

> Detailed report specifications are in Section 5B (Steps 9–10 of the evaluation pipeline). Below is the high-level overview.

### Dual Report Model

GoNoGo generates two reports from each scan:

**Report A (AI Handoff):** Machine-parseable markdown with exact selectors, file path hints, and zero-ambiguity fix instructions. Designed to be pasted directly into a coding AI.

**Report B (Human Review):** Rich, visual, contextual report with annotated screenshots, explanations of *why* things matter, and an encouraging tone. Designed for the developer to read and prioritize.

### Report Sections (Both Reports)

1. **Verdict** — GO / NO-GO / GO WITH CONDITIONS
2. **Overall Score** — 0–100 composite + letter grade + per-lens breakdown
3. **Executive Summary** — One paragraph overall impression
4. **What's Working Well** — Positive reinforcement, not just a roast session
5. **Critical Issues** — Broken or actively harmful to user experience
6. **Improvements** — Functional but suboptimal, ranked by impact
7. **Polish Suggestions** — Nice-to-haves that elevate "works" to "feels professional"
8. **Top 3 Actions** — If you only fix three things, fix these

### Tagging System
Each finding tagged with:
- **Category:** Function | Design | UX | Performance | Accessibility | Code | Content
- **Effort Estimate:** Quick Fix | Moderate | Significant
- **Priority:** Critical | High | Medium | Low
- **Confidence:** How sure the agent is about this finding

---

## 4. User Experience Flow

### The Core User Journey

```
1. LAND        → User arrives at the tool's page
2. INPUT       → Paste URL (required)
               → Optionally: write a brief in the text field
               → Optionally: upload sketches/mockups/notes/reference images
               → Optionally: specify a test route for the agent to follow
               → Optionally: specify tech stack
3. LAUNCH      → Hit "Run GoNoGo" (or similar CTA)
4. OBSERVE     → Status text updates showing current phase ("Running accessibility audit...")
               → Live progress feed toggle available (default OFF)
               → When ON: more detailed status updates on what the agent is doing
               → Negligible additional cost — no extra LLM calls, just broadcasting internal state
5. RECEIVE     → Two reports delivered as downloadable files:
               → Report A: AI-consumable markdown (download to feed to coding AI)
               → Report B: Human-readable report with visuals and explanations
```

### UX Notes
- The "specify a test route" option should be clearly presented but not required — the app should inform the user that they *can* direct the agent's focus if they want to
- **Live progress toggle:** Default OFF for simplicity. When ON, shows status text updates (e.g., "Now scanning /checkout...", "Running Lighthouse audit...", "Evaluating design quality..."). This costs virtually nothing extra — no additional LLM calls required, just the backend broadcasting what pipeline step it's on via SSE. The data is already being generated; the toggle just controls whether it's displayed.
- Reports delivered as downloadable files (primary delivery method)
- Reports should be shareable

---

## 5. Technical Architecture (Working Draft)

### Recommended Tech Stack

> These are recommendations based on what GoNoGo specifically needs. Subject to discussion and revision.

**Why these choices:** GoNoGo's backend has unusual requirements — it needs to orchestrate a headless browser, run long-lived async jobs (scans can take minutes), make multiple LLM calls per scan, stream real-time progress to the frontend, and store screenshots. The stack is optimized for those needs.

| Layer | Recommendation | Why |
|-------|---------------|-----|
| **Frontend** | **React + Vite** (or Next.js) | Lightweight SPA is sufficient — the heavy lifting is backend. Vite is fast to develop with. Next.js if you want SSR for a public marketing/landing page later |
| **Backend** | **Python (FastAPI)** | Best ecosystem for this job — Playwright has excellent Python support, Anthropic/OpenAI SDKs are Python-first, FastAPI handles async natively, easy subprocess calls to Lighthouse |
| **Browser Automation** | **Playwright (Python)** | More reliable than Puppeteer, built-in support for multiple browsers, excellent screenshot/network interception APIs, great async support |
| **Job Queue** | **Celery + Redis** (or for V1: simple background tasks with FastAPI) | Scans are long-running — can't block HTTP requests. Celery handles retries, timeouts, concurrency. For V1 personal use, FastAPI BackgroundTasks + SSE may suffice |
| **Real-time Progress** | **Server-Sent Events (SSE)** | Simpler than WebSockets for one-way server→client updates. Perfect for "the agent is now checking page X..." progress feed |
| **Database** | **SQLite → PostgreSQL** | SQLite for V1 (zero setup, personal use). Migrate to PostgreSQL when going public. Stores: scan history, user data, report metadata |
| **File Storage** | **Local filesystem → S3/Cloudflare R2** | Screenshots and reports need storage. Local for V1, object storage for production. R2 is cheap with no egress fees |
| **Performance/A11y Tools** | **Lighthouse CLI + axe-core** | Run via subprocess (Lighthouse) and Playwright injection (axe-core). Don't reinvent these — wrap and synthesize |
| **LLM** | **Gemini API (primary), Claude API (secondary option)** | Gemini 2.5 Pro for complex tasks (design, UX, synthesis, report gen). Gemini 2.5 Flash for simpler tasks (functionality, performance, accessibility, code/content, tech stack detection). Claude available as fallback/option. BYOK (Bring Your Own Key) model for public launch |
| **Hosting** | **Vercel (frontend) + Railway/VPS (backend)** | Vercel for frontend — free tier, deploy-on-push from GitHub. Backend needs persistent processes for Playwright (serverless won't work for 2–5 min scans), so Railway ($5–20/mo) or a VPS ($5–12/mo on Hetzner/DigitalOcean) |

**Architecture Pattern:**

```
[Frontend SPA] ←SSE→ [FastAPI Backend] → [Job Queue]
                                              ↓
                                    [Scan Worker Process]
                                     ├── Playwright (browser)
                                     ├── Lighthouse (perf)
                                     ├── axe-core (a11y)
                                     └── LLM API (evaluation)
                                              ↓
                                    [File Storage] (screenshots, reports)
                                              ↓
                                    [Database] (scan records, metadata)
```

### How the Agent "Sees" the App

These methods are complementary, not mutually exclusive:

| Method | Purpose |
|--------|---------|
| **Headless Browser Automation** (Playwright) | Navigation, clicking, screenshots, console errors, network requests — the foundation |
| **LLM Vision** (multimodal model) | Evaluate layout, design quality, visual hierarchy, "taste" — feed screenshots for subjective assessment |
| **DOM Analysis** | Parse HTML/CSS for semantic correctness, accessibility attributes, structural issues |
| **Existing Tool Integration** (Lighthouse, axe-core) | Don't reinvent the wheel for performance & accessibility metrics — wrap existing tools, let LLM synthesize into plain language |

### Key Technical Challenges
- **Cost Management:** Multiple LLM calls (especially vision) per scan — need to balance quality with API cost (see Cost Model below)
- **Scan Duration:** Full evaluation could take 2–5 minutes — UX accounts for this with async processing + optional progress feed

### Authentication Strategy

**Decision:** Credential form per scan — the simplest, most universal approach for a standalone tool.

**How it works:**
- Optional fields on the scan input form: username/password OR session token/cookie paste
- Playwright uses these credentials to log in through the app's normal login flow, just like a real user
- Credentials are used only for that scan session and discarded immediately after
- For V1 personal use: skip this entirely, test only public-facing routes
- Future: could support saved credentials per project for repeat scans

**Why not other approaches:**
- OAuth requires the target app to register GoNoGo as an authorized client (won't happen)
- Cookie injection is fragile and browser-specific
- A credential vault adds complexity without clear V1 value

### Exploration Depth Strategy

**Decision:** Page Type Mapping with representative deep-testing.

**How it works:**
1. **Crawl phase:** The agent discovers all navigable pages and categorizes them into **page types** (homepage, listing page, detail page, form page, settings page, dashboard, etc.)
2. **Deep-test one representative of each page type:** Full evaluation — screenshots, interactions, form submissions, error state testing
3. **Spot-check 2–3 additional pages per type:** Verify consistency — do all product pages use the same template? Are there outliers?
4. **Shallow-crawl everything else:** Just check for 404s, broken images, console errors, basic health signals
5. **Test each unique interaction pattern once:** If there are 50 product pages with the same "Add to Cart" button, test it once deeply, not 50 times

**Stopping Rules (configurable):**
- Max **30 pages** deep-tested
- Max **100 pages** shallow-crawled
- Max **10 minutes** total scan time
- Agent declares "done" when all discovered page types have been deep-tested and all specified user routes have been walked

**Why this works:** It avoids wasting time on repetitive content while ensuring every *kind* of experience in the app gets thorough evaluation. A 50-page e-commerce site with 40 product pages doesn't need 40 deep evaluations — it needs 1 deep evaluation of the product page template + a few consistency checks.

### Agent Personality & Tone

**Decision:** Opinionated and direct. Like a reliable, competent senior colleague who sincerely wants you to be better.

**Tone guidelines for Report B (human-readable):**
- Says exactly what's on its mind — no hedging, no corporate softness
- Direct but not cruel — the goal is improvement, not humiliation
- Gives credit where it's due — acknowledges good work with specificity
- When something is bad, explains *why* it matters and *how* to fix it
- Talks like a person, not a tool — "This checkout flow will lose you customers" not "Suboptimal conversion pathway detected"
- Treats the builder as a peer working on something that matters

**Tone for Report A (AI-consumable):** No personality — pure structured instructions. Personality lives only in Report B.

### Sketch-to-Live Comparison Strategy

**Decision:** Conceptual comparison, not pixel-level.

**How it works:**
- The agent compares the *intent* expressed in uploaded materials against the *reality* of the live app
- Uploaded images may contain: mockups, wireframes, sketches, handwritten notes with text, spec documents, reference screenshots
- The agent uses LLM vision to *read and interpret* any text in uploaded images (handwritten notes, annotations, spec text)
- Comparison is layout-based and conceptual: "The sketch shows a 3-column grid but the live site uses a 2-column layout" or "The notes specify a dark mode toggle but none exists"
- NOT pixel-perfect comparison — no overlay diffing or pixel-level matching

### Scan History

**Decision:** Yes — build it in from V1. Low cost, high value.

**Resource impact:**
- Each scan stores: ~2–5MB (two markdown reports + 10–30 screenshots at ~50KB each + metadata JSON)
- Database record per scan: tiny (scores, timestamp, URL, verdict, prompt versions)
- 100 scans = ~500MB total storage — trivial
- Comparison feature: frontend rendering job comparing score objects between scans. No ongoing compute cost.
- No significant upkeep cost — just storage, which is cents per GB

**Features:**
- Save all scan reports with timestamps
- View scan history per project/URL
- Compare two scans side-by-side to see what improved and what regressed
- Track scores over time (simple line chart per lens)

### Prompt Version Control

**Decision:** Yes — version prompts alongside code in the repo.

**Who creates the prompts:** The AI assistant (Claude) drafts all prompts for every pipeline step — the full evaluation rubrics, persona instructions, output schemas, calibration examples, everything. These are internal system prompts that power GoNoGo's intelligence. **The user never sees them — they're backend code.** The founder then tests the prompts against real sites, identifies where output is weak or wrong, and the prompts get refined collaboratively. Workflow: **AI drafts the brain → founder QA's the QA tool → iterate together until sharp.**

**The prompts ARE the product.** GoNoGo's value lives almost entirely in the quality of these prompts. Version controlling them is non-negotiable.

**Implementation:**
```
/prompts/
  ├── intent_analysis_v1.md
  ├── tech_stack_detection_v1.md
  ├── functionality_lens_v1.md
  ├── design_lens_v1.md
  ├── ux_lens_v1.md
  ├── performance_lens_v1.md
  ├── accessibility_lens_v1.md
  ├── code_content_lens_v1.md
  ├── synthesis_v1.md
  ├── report_generation_v1.md
  └── CHANGELOG.md
```

**How it works:**
- Each prompt template is a versioned file in the repo (e.g., `design_lens_v3.md`)
- Templates contain the full prompt with `{{placeholders}}` for dynamic data (screenshots, recon data, etc.)
- Each scan record stores which prompt versions were used: `{ "design": "v3", "functionality": "v2", ... }`
- When a prompt is improved, bump the version number and commit
- A/B testing: run the same site through v2 and v3 of a lens, compare results
- `CHANGELOG.md` documents what changed in each version and why
- If a new version produces worse results, roll back to the previous version instantly

### Calibration Dataset

**Decision:** Yes — 5 curated reference sites spanning quality spectrum.

**Baseline ownership:** The AI assistant (Claude) will create the initial baseline evaluations — manually evaluating each calibration site across all seven lenses, writing expected findings, assigning expected scores, and documenting the ground truth. The founder reviews and approves.

**Ongoing calibration:** Requires periodic revisiting as prompts evolve. **The founder has requested explicit reminders to revisit calibration over time** — this is easy to neglect but critical for quality. Calibration should be re-run after any significant prompt version change.

**Starting approach:**
1. **One of your own BaryApps tools** — you know the intent, the flaws, everything. Best possible calibration target.
2. **A polished, well-known site** (e.g., stripe.com, linear.app) — should score high across most lenses
3. **A decent indie project** (from Product Hunt or Indie Hackers) — good but imperfect, realistic target user quality level
4. **A deliberately rough MVP** (a weekend hackathon project, an unstyled prototype) — should score low, tests whether the agent catches obvious issues
5. **A site with known accessibility problems** — tests the accessibility lens specifically

**Process:**
- AI assistant creates ground truth documents for each site (expected findings, scores, verdict)
- Founder reviews and adjusts ground truth based on their own judgment
- Run GoNoGo against each site
- Compare agent output vs. ground truth
- Where they diverge, tune the prompts
- Re-run and iterate until alignment is strong
- This becomes the regression test suite — run it whenever prompts change to prevent regressions

---

### Cost Per Scan Model

> Based on Gemini API pricing as of February 2026. Prices will likely decrease over time.

**Pricing used:**
- Gemini 2.5 Pro: $1.25 / 1M input tokens, $10.00 / 1M output tokens
- Gemini 2.5 Flash: $0.50 / 1M input tokens, $3.00 / 1M output tokens

**Token estimates per pipeline step:**

| Step | Model | Input Tokens | Output Tokens | Cost |
|------|-------|-------------|---------------|------|
| **Step 0: Recon** | None (automation) | — | — | $0.00 |
| **Step 1: Intent Analysis** | Pro | ~4,000 | ~800 | ~$0.013 |
| **Step 2: Tech Stack** | Flash | ~1,400 | ~400 | ~$0.002 |
| **Step 3: Functionality** | Flash | ~5,300 | ~3,000 | ~$0.012 |
| **Step 4: Design Quality** | Pro | ~18,000 | ~4,000 | ~$0.063 |
| **Step 5: UX Flow** | Pro | ~13,200 | ~3,000 | ~$0.047 |
| **Step 6: Performance** | Flash | ~4,000 | ~2,000 | ~$0.008 |
| **Step 7: Accessibility** | Flash | ~4,000 | ~2,000 | ~$0.008 |
| **Step 8: Code/Content** | Flash | ~6,800 | ~2,500 | ~$0.011 |
| **Step 9: Synthesis** | Pro | ~17,300 | ~3,000 | ~$0.052 |
| **Step 10: Report Gen** | Pro | ~21,200 | ~10,000 | ~$0.127 |

**Subtotals:**
- Gemini 2.5 Pro: ~73,700 input + ~20,800 output = **~$0.30**
- Gemini 2.5 Flash: ~21,500 input + ~9,900 output = **~$0.04**

**Raw cost per scan: ~$0.34**

**With 1.5× buffer** (thinking tokens, retries, edge cases): **~$0.50 per scan**

**Cost ranges by site complexity:**

| Site Size | Estimated Cost | Notes |
|-----------|---------------|-------|
| Small (5–10 pages) | $0.25 – $0.35 | Fewer screenshots, less content to analyze |
| Medium (10–30 pages) | $0.40 – $0.60 | Typical scan |
| Large/Complex (30+ pages) | $0.60 – $1.00 | More page types, longer recon, more findings |

**Monthly cost for personal use:**
- 5 scans/month: ~$2.50
- 20 scans/month: ~$10
- 50 scans/month: ~$25

### Pricing Model

**Decision:** BYOK (Bring Your Own Key) as primary model, with a hosted option later.

**V1 (Personal Use):**
- You use your own Gemini API key
- Zero platform cost — you pay only the API cost (~$0.50/scan)

**V2 (Public Launch) — Hybrid Model:**
- **BYOK tier (free):** Users provide their own Gemini API key. GoNoGo charges nothing — the user pays their own API costs directly. Lower friction for developers who already have API keys.
- **Hosted tier (paid):** GoNoGo provides the LLM access. Users pay per scan with a margin built in. Suggested pricing: **$2–5 per scan** (covering ~$0.50 cost + margin + infrastructure). This tier is for users who don't want to deal with API keys.
- **Subscription option (future):** Unlimited scans for a monthly fee. Would need to model based on usage patterns. Rough estimate: $19–29/month for ~50 scans, $49–79/month for unlimited.

**Why BYOK first:** It eliminates the biggest cost risk (LLM API spend) while you validate the product. Users who need this tool are developers — they're comfortable with API keys. The hosted tier comes later for the broader audience (students, less technical vibe coders).

---

## 5B. The Agent's Brain — Evaluation Pipeline

> This is the core intelligence of GoNoGo. Everything else is infrastructure — this is the product.

### Architecture Decision: Multi-Step Pipeline (Not a Single Mega-Prompt)

A single prompt that says "evaluate this entire app" will produce inconsistent, shallow results. Instead, GoNoGo uses a **multi-step pipeline** where each phase has a specific job, specific inputs, and structured outputs.

**Why a pipeline:**
- Each evaluation lens requires different data and different analytical approaches
- Breaking it up allows quality control at each step — if one lens produces weak output, it can be re-run without redoing everything
- Individual lenses can be iterated and improved independently
- Token limits stay manageable (screenshots are expensive in tokens)
- Steps can be parallelized where they don't depend on each other
- The pipeline steps naturally map to the live progress feed ("Now evaluating: Design Quality...")
- Easier to debug — you can see exactly where the evaluation went wrong

### The Pipeline: 10 Steps

```
STEP 0: Reconnaissance (no LLM)
    ↓
STEP 1: Intent Analysis (LLM)
    ↓
STEP 2: Tech Stack Detection (LLM + heuristics)
    ↓
┌───────────────────────────────────────────┐
│ STEPS 3–8: Lens Evaluations (parallel OK) │
│  3. Functionality                         │
│  4. Design Quality                        │
│  5. UX Flow                               │
│  6. Performance                           │
│  7. Accessibility                         │
│  8. Code Quality & Content                │
└───────────────────────────────────────────┘
    ↓
STEP 9: Synthesis & Scoring (LLM)
    ↓
STEP 10: Dual Report Generation (LLM)
```

---

### STEP 0: Reconnaissance (No LLM — Pure Automation)

**Purpose:** Gather all raw data before any AI evaluation begins. This is the foundation everything else builds on.

**Tools:** Playwright, Lighthouse CLI, axe-core

**Actions:**
- Crawl the site: discover all navigable pages (respect depth/page limits)
- For each page:
  - Full-page screenshot (desktop viewport)
  - Mobile viewport screenshot (375px width)
  - DOM snapshot (full HTML)
  - Computed styles for key elements
  - Console log capture (errors, warnings)
  - Network request log (failed requests, slow resources, 404s, mixed content)
- If user specified a test route: follow that route step-by-step, capturing state at each step
- Run Lighthouse audit (performance, SEO, best practices scores + detailed metrics)
- Inject and run axe-core (accessibility violations, warnings, passes)
- Extract: all links (internal + external) and their status codes, all images and their alt text, all form elements, all interactive elements
- Extract: meta tags, Open Graph tags, favicon, manifest, robots.txt, sitemap.xml
- Detect: framework signatures (Next.js, React, Vue, WordPress, etc. from script tags, headers, DOM patterns)

**Output:** A structured `recon_data` object containing everything above. This is the raw evidence base.

**Duration estimate:** 30–120 seconds depending on site size.

---

### STEP 1: Intent Analysis (LLM)

**Purpose:** Understand what this project is trying to be and who it's for. This frames every subsequent evaluation.

**Inputs to LLM:**
- User's text brief (if provided)
- User's uploaded sketches/mockups (if provided)
- Homepage screenshot
- Meta tags, OG tags, page titles
- Navigation structure (inferred from crawl)
- First 500 words of visible text content

**Prompt Design Principles:**
- Ask the LLM to output structured JSON, not prose
- Force it to commit to specific assessments, not hedge

**Expected Output Schema:**
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
    "Land on homepage → Understand brand → Browse collection",
    "Search for specific product → Find it → Purchase"
  ],
  "success_criteria": [
    "User can find and purchase a product without confusion",
    "Brand identity is clear and consistent",
    "Trust signals are present (reviews, secure checkout, return policy)"
  ],
  "intent_vs_execution_gaps": [
    "User sketches show a minimalist aesthetic but live site uses 4 different fonts",
    "Brief mentions 'premium feel' but product images are low resolution"
  ],
  "confidence": 0.85
}
```

**Key:** If the user provided sketches/mockups, this step explicitly compares intent (sketches) vs. reality (screenshots) and flags discrepancies. This becomes a powerful input for the Design Quality lens.

---

### STEP 2: Tech Stack Detection (LLM + Heuristics)

**Purpose:** Identify how the app is built so Report A can reference the correct file structures, component patterns, and framework-specific fixes.

**Inputs:**
- User-provided tech stack (if given)
- Framework signatures from recon (script tags, meta generators, CDN URLs, HTTP headers)
- DOM patterns (e.g., `data-reactroot`, `__nuxt`, `wp-content`)
- Package/bundle analysis if source maps are available

**Output Schema:**
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

**Why this matters:** If GoNoGo knows it's a Next.js app, Report A can say "In your `app/checkout/page.tsx`, the form submission handler..." instead of generic "somewhere in your code."

---

### STEPS 3–8: Lens Evaluations

> These are the seven evaluation lenses. Each gets its own LLM call with tailored inputs and a specific rubric. Steps 3–8 can run in parallel since they don't depend on each other (only on Steps 0–2).

#### General Design Pattern for All Lens Evaluations

Every lens evaluation follows the same structure:

```
INPUT:  Relevant subset of recon_data + intent_analysis + tech_stack
PROMPT: Rubric-driven evaluation with specific criteria
OUTPUT: Structured findings in a consistent schema
```

**Universal Finding Schema** (every finding from every lens uses this):
```json
{
  "id": "FUNC-001",
  "lens": "functionality",
  "severity": "critical|high|medium|low",
  "effort": "quick_fix|moderate|significant",
  "title": "Checkout form submits but shows no confirmation",
  "description": "After clicking 'Place Order', the page reloads but displays no success message, error, or redirect. User has no idea if the order went through.",
  "evidence": {
    "page_url": "/checkout",
    "screenshot_ref": "screenshot_checkout_post_submit.png",
    "dom_selector": "form#checkout-form",
    "console_errors": ["Uncaught TypeError: Cannot read property 'id' of undefined"],
    "network_evidence": "POST /api/orders returns 500"
  },
  "recommendation": {
    "human_readable": "Add a success state after form submission — either redirect to an order confirmation page or show an inline success message with the order details.",
    "ai_actionable": "In the checkout form submit handler, add response validation and a success state. After a successful POST to /api/orders, either router.push('/order-confirmation/${orderId}') or set a state variable to render a confirmation component. Also handle the 500 error — the API endpoint likely has a null reference bug."
  }
}
```

**Key design decisions in this schema:**
- `evidence` anchors every finding to something observable — no vague claims
- `recommendation` has TWO versions: one for the human (Report B), one for the AI (Report A)
- `dom_selector` and `page_url` make findings machine-locatable
- `screenshot_ref` links to annotated screenshots where relevant

---

#### STEP 3: Functionality Lens

**What it evaluates:** Does the app work? Are things broken?

**Inputs:** Console errors, network request log (failed requests, 404s, 500s), link audit results, form element inventory, interactive element states

**Rubric:**
- Are there JavaScript errors in the console? (for each: what triggers it, what's the impact?)
- Do all internal links resolve? (list any 404s, redirects to wrong pages)
- Do all external links work? (broken outbound links)
- Do forms submit successfully? (test with valid and invalid input)
- Do interactive elements respond? (buttons, dropdowns, modals, accordions)
- Are there dead ends? (pages with no navigation back, or actions that lead nowhere)
- Are images loading? (broken image references)
- Does the app work without JavaScript? (progressive enhancement check)

**LLM Role:** The recon data already captures most functional issues mechanically. The LLM's job here is to *interpret severity and context* — a 404 on a rarely-visited legal page is medium priority; a broken checkout button is critical.

---

#### STEP 4: Design Quality Lens

**What it evaluates:** Does it look good? Is it visually consistent and professional?

**Inputs:** Full-page screenshots (desktop + mobile), intent analysis (especially any uploaded sketches), computed styles for key elements

**Rubric:**
- **Color consistency:** Is there a coherent color palette? How many colors are used? Do they clash?
- **Typography:** How many font families? Are sizes consistent across similar elements? Is hierarchy clear (H1 > H2 > H3 > body)?
- **Spacing:** Is spacing consistent? Are there awkward gaps or cramped areas? Does it follow a visible rhythm?
- **Visual hierarchy:** Can you tell what's most important on each page? Do CTAs stand out?
- **Component consistency:** Do similar elements (cards, buttons, inputs) look the same throughout?
- **Image quality:** Are images crisp, properly sized, and consistent in style? Any pixelation, stretching, or mismatched aspect ratios?
- **Overall polish:** Does it feel finished or template-y? Are there obvious default styles left in?
- **Intent vs. execution:** If sketches/mockups were provided, how well does the live design match the intended vision?

**LLM Role:** This is where LLM vision capabilities are essential. Feed screenshots + rubric + intent analysis. The LLM acts as a design reviewer with "taste." This is the lens that most differentiates GoNoGo from existing tools.

**Prompt Strategy:** Ask the LLM to evaluate as a senior product designer reviewing a portfolio piece. Be specific and constructive, not vague. "The spacing is off" is useless. "The card grid uses inconsistent padding — cards 1 and 3 have 24px padding while cards 2 and 4 have 16px" is actionable.

---

#### STEP 5: UX Flow Lens

**What it evaluates:** Can a user figure out what to do? Is the experience intuitive?

**Inputs:** Screenshots in navigation sequence, site map (from crawl), intent analysis (key user journeys), interactive element inventory

**Rubric:**
- **First impression (5-second test):** If a new user lands on the homepage, can they tell what this app does and what they should do first?
- **Navigation clarity:** Is the nav structure logical? Can the user get to key pages within 2-3 clicks?
- **CTA clarity:** Are calls-to-action obvious? Is there a clear primary action on each page?
- **Form UX:** Are forms easy to fill? Good labels, helpful placeholders, clear validation messages, appropriate input types?
- **Error states:** What happens when things go wrong? Are error messages helpful or generic?
- **Loading states:** Are there loading indicators for async operations? Or does the UI just freeze?
- **Empty states:** What does the app look like with no data? Is it helpful or confusing?
- **Mobile UX:** Is the experience good on mobile, or just a squeezed desktop layout? Touch targets adequate?
- **Onboarding:** If the app requires setup/registration, is the onboarding flow smooth?
- **Dead ends & confusion points:** Are there moments where a user would think "now what?"

**LLM Role:** The LLM "walks through" the key user journeys identified in Step 1, examining the screenshot sequence and flagging friction points. It should think like a first-time user, not a developer.

---

#### STEP 6: Performance Lens

**What it evaluates:** Is the app fast and efficient?

**Inputs:** Lighthouse performance report, network request log (sizes, timing), resource analysis

**Rubric:**
- **Core Web Vitals:** LCP, FID/INP, CLS — are they in green/yellow/red ranges?
- **Total page weight:** How large is the initial load? Are there oversized assets?
- **Image optimization:** Are images served in modern formats (WebP/AVIF)? Are they properly sized for their display dimensions? Lazy loading implemented?
- **JavaScript bundle:** How large? Is there obvious dead code or oversized dependencies?
- **Render-blocking resources:** Are CSS/JS files blocking first paint unnecessarily?
- **Caching:** Are cache headers set appropriately for static assets?
- **Network waterfall:** Are there obvious bottlenecks? Sequential requests that could be parallelized?

**LLM Role:** Lighthouse provides the raw data. The LLM's job is to translate technical metrics into *prioritized, actionable advice* with clear impact estimates. "Your hero image is 2.4MB and served as PNG. Converting to WebP and resizing to the actual display dimensions (~800px wide) would reduce it to ~120KB, cutting your LCP by approximately 1.5 seconds." That's the quality bar.

---

#### STEP 7: Accessibility Lens

**What it evaluates:** Can everyone use this app, including people with disabilities?

**Inputs:** axe-core audit results, DOM snapshots, computed styles (for contrast), interactive element inventory

**Rubric:**
- **Color contrast:** Do all text/background combinations meet WCAG AA (4.5:1 for normal text, 3:1 for large text)?
- **Alt text:** Do all meaningful images have descriptive alt text? Are decorative images marked appropriately?
- **Keyboard navigation:** Can all interactive elements be reached and operated with keyboard alone? Is focus order logical? Are focus styles visible?
- **Semantic HTML:** Are headings used in proper hierarchy? Are landmarks present (nav, main, footer)? Are lists marked up as lists?
- **ARIA usage:** Is ARIA used correctly, or is it misapplied? (Bad ARIA is worse than no ARIA)
- **Form labels:** Are all form inputs properly labeled? Are required fields indicated?
- **Screen reader experience:** Would the page make sense when read linearly? Are dynamic content changes announced?
- **Motion/animation:** Is there a prefers-reduced-motion media query? Are animations excessive?

**LLM Role:** axe-core catches the mechanical violations. The LLM adds context — "This missing alt text is on your primary product images, meaning screen reader users can't browse your store" vs. "This missing alt text is on a decorative divider, which is lower priority."

---

#### STEP 8: Code Quality & Content Lens

**What it evaluates:** Is the code clean? Is the content polished?

**Inputs:** DOM snapshots, meta tags, visible text content, page titles, detected tech stack

**Code Quality Rubric:**
- **Semantic HTML:** Are elements used for their intended purpose? (div-soup vs. proper semantics)
- **Meta tags & SEO:** Title tags, meta descriptions, OG tags, canonical URLs, structured data
- **Responsive implementation:** Is it using proper responsive techniques or just hiding overflow?
- **Console cleanliness:** Development console.logs left in? Warning spam?
- **Resource loading:** Efficient script loading (defer, async)? Font loading strategy?

**Content Quality Rubric:**
- **Placeholder content:** Any "Lorem ipsum," "TODO," "asdf," or obviously placeholder text?
- **Spelling & grammar:** Typos, grammatical errors, inconsistent capitalization
- **Tone consistency:** Does the copy feel like it was written by one voice or patchworked together?
- **Missing content:** Empty sections, missing images, "coming soon" placeholders
- **Microcopy:** Are button labels, error messages, and helper text clear and useful?

**LLM Role:** Mix of mechanical detection (placeholder text, meta tag presence) and subjective evaluation (tone consistency, copy quality).

---

### STEP 9: Synthesis & Scoring (LLM)

**Purpose:** Take all findings from Steps 3–8, deduplicate, resolve conflicts, assign final priorities, and generate overall scores.

**Inputs:** All findings from all lenses + intent analysis

**Actions:**
- Deduplicate: sometimes the same root issue surfaces in multiple lenses (e.g., a missing alt text appears in both Accessibility and Code Quality). Merge these into a single finding with multiple lens tags.
- Priority ranking: consider severity × impact × effort. A critical functional bug that's a quick fix should rank above a medium design issue that requires significant rework.
- Cross-lens patterns: identify systemic issues ("the app generally lacks loading states" is more useful than 5 separate findings about individual missing loaders)
- Generate scores:

**Scoring Model (per lens + overall):**
```json
{
  "overall_score": 72,
  "overall_grade": "C+",
  "verdict": "NO-GO",
  "verdict_reasoning": "Critical functional bugs in the checkout flow make this unsafe to ship. Design and UX are solid foundations but need polish.",
  "lens_scores": {
    "functionality": { "score": 45, "grade": "F", "summary": "Critical bugs in core flow" },
    "design": { "score": 78, "grade": "B", "summary": "Good foundations, inconsistent execution" },
    "ux": { "score": 70, "grade": "C+", "summary": "Happy path works, edge cases neglected" },
    "performance": { "score": 82, "grade": "B+", "summary": "Fast, minor optimizations possible" },
    "accessibility": { "score": 60, "grade": "D", "summary": "Multiple WCAG AA failures" },
    "code_quality": { "score": 75, "grade": "B-", "summary": "Clean structure, SEO gaps" },
    "content": { "score": 88, "grade": "A-", "summary": "Well-written, minor typos" }
  },
  "top_3_actions": [
    "Fix the checkout form submission bug (FUNC-001) — this blocks all purchases",
    "Add alt text to product images (A11Y-003) — 40+ images affected",
    "Reduce hero image size from 2.4MB (PERF-002) — biggest single performance win"
  ]
}
```

**The GO / NO-GO Verdict:**
This is the signature moment — the tool's namesake. Based on all lens scores and critical findings:
- **GO:** The app is ready to ship. There may be improvements to make, but nothing is blocking.
- **NO-GO:** There are critical issues that should be fixed before launch. The report explains exactly what and why.
- **GO WITH CONDITIONS:** Shippable, but specific issues should be addressed within a defined timeframe.

---

### STEP 10: Dual Report Generation (LLM)

**Purpose:** Transform the synthesized findings into two distinct reports for two distinct audiences.

**Input:** All synthesized findings + scores + verdict from Step 9

#### Report A: AI-Consumable (Agent Handoff)

**Format:** Structured markdown, parseable, no ambiguity

**Structure:**
```markdown
# GoNoGo Report — [Project Name]
## Verdict: NO-GO
## Tech Stack: Next.js, Tailwind CSS, Supabase

### Critical (fix before launch)
#### FUNC-001: Checkout form fails silently
- Page: /checkout
- Selector: form#checkout-form
- Issue: POST /api/orders returns 500, no error handling in submit handler
- Fix: Add try/catch in submit handler, validate API response, show success/error state
- File hint: app/checkout/page.tsx (Next.js App Router pattern)

#### A11Y-003: Product images missing alt text
- Pages: /products, /products/[id]
- Selector: img.product-image
- Issue: 43 product images have empty alt attributes
- Fix: Add descriptive alt text from product name + variant. Example: alt="Lavender Dreams soy candle, 8oz"
...
```

**Design principles for Report A:**
- Every finding is a discrete, actionable instruction
- Include selectors, file path hints, and specific code suggestions
- A coding AI should be able to fix every item without asking "what do you mean?"
- No conversational tone — pure signal

#### Report B: Human-Readable (User Review)

**Format:** Rich markdown with embedded screenshots and visual annotations

**Structure:**
```markdown
# GoNoGo Report — [Project Name]
## Overall: 72/100 (C+) — NO-GO

### Executive Summary
Your candle store has strong visual foundations and well-written copy, but critical 
bugs in the checkout flow make it unsafe to launch...

### What's Working Well
- Clean, cohesive brand identity across pages
- Product photography is high-quality and consistent
- Copy is warm, authentic, and speaks to the target audience
...

### Critical Issues
[Annotated screenshot showing the broken checkout state]
**The checkout form fails silently** — after clicking "Place Order," nothing 
happens. No confirmation, no error, no redirect. A customer would have no idea 
if their order went through. This is the single most important fix...
...
```

**Design principles for Report B:**
- Lead with the big picture — what works, what doesn't, overall feeling
- Use annotated screenshots for visual/design/UX findings
- Explain *why* things matter, not just *what* is wrong
- Prioritize by impact — the user should be able to read just the first 3 findings and get 80% of the value
- Encouraging tone — this is a tool for builders, not a blame machine

---

### Prompt Engineering Principles (Across All Steps)

These principles govern how every LLM call in the pipeline is designed:

1. **Structured output always.** Every prompt requests JSON or structured markdown. Never rely on the LLM to self-organize prose output. Parse and validate every response.

2. **Rubric-driven, not vibes-driven.** Instead of "evaluate the design," give specific criteria: "Score visual consistency 1–5 based on: consistent color palette (Y/N), consistent typography (Y/N), consistent spacing (Y/N), consistent component styling (Y/N)." This grounds evaluation in observable evidence.

3. **Evidence-required.** Every finding must reference specific evidence — a screenshot, a DOM element, a console error, a URL. If the LLM can't point to evidence, the finding gets discarded. No "the design could be better" without saying exactly what and where.

4. **Dual recommendations.** Every finding produces two recommendation versions — one for a human reader, one for a coding AI. Written simultaneously from the same analysis.

5. **Persona injection.** Each lens prompt includes a persona that shapes the evaluation perspective:
   - Functionality: "You are a QA engineer testing this app before launch."
   - Design: "You are a senior product designer reviewing this for a portfolio critique."
   - UX: "You are a first-time user who has never seen this app before."
   - Performance: "You are a web performance consultant auditing this site."
   - Accessibility: "You are an accessibility specialist evaluating WCAG 2.1 AA compliance."
   - Code/Content: "You are a senior frontend developer doing a code review."

6. **Context window management.** Screenshots are token-expensive. Each lens only receives the screenshots it needs — the Design lens gets all screenshots, the Functionality lens gets only screenshots of error states, the Performance lens gets none (it works from metrics).

7. **Calibration through examples.** Each lens prompt includes 1–2 examples of good findings vs. bad findings to calibrate quality. Example: "BAD: 'The colors are off.' GOOD: 'The primary CTA button (#4A90D2) against the hero background (#3B7DD8) has a contrast ratio of only 1.3:1, making it nearly invisible. Recommend changing button color to #FFFFFF or #1A1A2E for a contrast ratio above 4.5:1.'"

8. **Confidence scoring.** Each finding includes a confidence level. If the LLM isn't sure about something (e.g., can't tell if a visual element is intentional or a bug), it flags it as lower confidence so the human report can present it as "potential issue" rather than a definitive finding.

9. **Iterative refinement built in.** After the initial evaluation, the pipeline includes a self-review step where the LLM reviews its own findings against the original evidence and prunes anything that doesn't hold up.

---

## 6. Strategic Decisions

### Scope & Platform Roadmap

| Phase | Platform | Notes |
|-------|----------|-------|
| **V1 (Now)** | Web App | Primary build target, fastest to ship and iterate |
| **V2** | Desktop Application | Port to standalone app for richer local capabilities |
| **V3** | Mobile App | When it makes sense — likely for report viewing/management, not core testing |

### Depth Strategy (V1)
- **Decision:** Both deep-dive AND broad sweep from V1
- **Rationale:** Move fast, need an agent that works hard alongside the builder
- **Risk:** Scope creep — will need to define clear "good enough" thresholds for V1

### V1 Definition of Done

V1 is considered **successful** when:

> The agent evaluates one of the existing BaryApps tools and produces a dual report (AI-consumable + human-readable) where the AI report can be handed directly to Claude (or another coding AI) to implement fixes — and the fixes are actually correct, relevant, and useful.

**Concrete test:** Pick an existing BaryApps tool → run the agent → take Report A → paste it into a coding AI → the coding AI understands every finding and can act on it without asking for clarification. If that works, V1 ships.

### Output Strategy — Dual Report Model

> Fully specified in Section 5B, Steps 9–10.

- **Report A (AI Handoff):** Structured, machine-parseable, zero-ambiguity. Includes selectors, file path hints, specific code fixes.
- **Report B (Human Review):** Visual, contextual, encouraging. Includes annotated screenshots and impact explanations.
- **GO / NO-GO / GO WITH CONDITIONS verdict** — the product's signature moment.

### User & Business Model

| Attribute | Detail |
|-----------|--------|
| **Initial User** | Personal tool (dogfooding) |
| **Future Users** | Vibe coders, solo developers, students |
| **Business Model** | Paid tool, part of a larger suite of tools |
| **Launch Strategy** | Personal use → confidence in value → public paid launch |

### Parent Brand: BaryApps

This QA agent is one tool within **BaryApps** — a collection of small to medium scale apps and tools for daily work and productivity.

**BaryApps Architecture Model:**
- BaryApps functions as the **"desktop"** — a central hub/repository where all tools are listed and discoverable
- Each tool **lives at its own URL / deployment** — independently hosted, independently accessible
- Tools are accessible both through BaryApps and through their own direct means (direct URL, standalone access)
- Think of it like a curated app store where each app is its own self-contained product

**Existing BaryApps Tools:**
- There are already tools built under BaryApps — this QA agent will be used to evaluate and improve those existing tools (immediate dogfooding opportunity)

**BaryApps Implications for This Tool:**
- Does NOT need to be embedded in a monolith — ships as its own standalone web app at its own URL
- Should share a consistent design language with other BaryApps tools for brand cohesion
- Shared infrastructure (auth, billing) can be integrated later when the public launch happens
- Listed on BaryApps hub, but fully functional independently

### Competitive Positioning

**Philosophy:** "I identified that I need this tool, and if I need it, other people who work like me will need it too." Competition is irrelevant to the decision to build — the tool gets built regardless, in the way that works best for the creator.

**Differentiators (emerging):**
- Holistic evaluation (not just performance OR accessibility — everything including subjective design taste)
- AI-consumable output (structured markdown designed to be fed directly to another AI for implementation)
- Built by a vibe coder, for vibe coders — understands the workflow of AI-assisted development
- Part of a broader tool ecosystem (BaryApps), not a standalone point solution

---

## 7. Open Questions & Decisions Needed

> Items below need to be resolved before or during development.

### Resolved
- [x] **Project Input Format:** Three-channel input + optional tech stack field. File upload accepts any reference material (mockups, notes, specs, sketches), not just design files.
- [x] **Tool Suite Context:** Part of BaryApps — a decentralized collection of independently-deployed tools with a central hub.
- [x] **BaryApps Architecture:** Hub/"desktop" model — each tool lives at its own URL, BaryApps is the directory. Not a monolith.
- [x] **Report Format:** Dual-report model — Report A for AI consumption (structured, precise, machine-parseable), Report B for human review (visual, contextual, explanatory).
- [x] **User Flow:** URL → optional brief + uploads + test route + tech stack → Run GoNoGo → optional progress feed → dual reports downloaded.
- [x] **First Dogfooding Targets:** Existing BaryApps tools will be the first projects evaluated by this agent.
- [x] **Tech Stack Detection:** Dual approach — agent infers autonomously AND user can optionally specify.
- [x] **V1 Definition of Done:** Agent evaluates a BaryApps tool → produces dual report → Report A is handed to a coding AI → fixes are correct and actionable.
- [x] **Tool Naming:** **GoNoGo** — from the go/no-go launch decision framework.
- [x] **Scoring System:** Per-lens scores (0–100 + letter grade) + overall composite + GO / NO-GO / GO WITH CONDITIONS verdict.
- [x] **Agent Architecture:** Multi-step pipeline (10 steps), not a single mega-prompt. Rubric-driven, evidence-required, structured output.
- [x] **Authentication Handling:** Credential form per scan (username/password or session token). Used for that scan only, discarded after. V1 tests public routes only.
- [x] **LLM Provider & Model:** Gemini API primary (2.5 Pro for complex tasks, 2.5 Flash for simpler ones). Claude API as secondary option. BYOK model.
- [x] **Exploration Depth Limits:** Page type mapping — deep-test one representative per type, spot-check 2–3 more, shallow-crawl rest. Max 30 deep, 100 shallow, 10 min.
- [x] **Pricing Model:** BYOK (free, users bring own key) for V1 + public launch. Hosted tier ($2–5/scan) for users who don't want API keys. Subscription option later.
- [x] **Tech Stack:** Approved — Python/FastAPI, Playwright, React+Vite, Redis/Celery, Vercel (frontend) + Railway/VPS (backend).
- [x] **Sketch-to-Live Comparison:** Conceptual comparison via LLM vision. Reads text in uploaded images (handwritten notes, annotations). Not pixel-level.
- [x] **Agent Personality / Tone:** Opinionated and direct. Like a reliable senior who sincerely wants you to be better. Personality in Report B only; Report A is pure structured data.
- [x] **Scan History:** Yes — low cost (~2–5MB per scan), high value. Includes comparison and tracking over time.
- [x] **Live Progress Feed:** Status text via SSE. Toggle available, default OFF. Negligible cost — no extra LLM calls.
- [x] **Report Delivery:** Download buttons (primary delivery method).
- [x] **Prompt Version Control:** Yes — versioned files in `/prompts/` directory, tracked per scan record. AI assistant drafts all prompts; founder tests and iterates. CHANGELOG.md tracks changes.
- [x] **Calibration Dataset:** Yes — 5 reference sites. AI assistant creates baseline ground truth. Founder reviews. AI assistant will proactively remind founder to revisit calibration.
- [x] **Cost Per Scan Estimate:** ~$0.50 average per scan (Gemini API). $0.25–$1.00 range depending on site complexity.

### Unresolved
- [ ] **Domain:** gonogo.app? gonogo.dev? gonogo.tools? Need to check availability and decide.
- [ ] **Logo & Visual Identity:** Direction TBD — aviation/launch metaphor? Green light/red light? Minimal?
- [ ] **Gemini Model Versions:** Lock to specific model versions or use latest? Affects reproducibility vs. quality improvements.
- [ ] **Rate Limiting:** How many concurrent scans can the backend handle? Affects infrastructure sizing.
- [ ] **Error Handling UX:** What happens when a scan fails mid-way? Partial report? Retry? Refund?

---

## 8. Conversation Log & Key Decisions

### Session 1 — February 13, 2026

**Topics Covered:**
- Initial concept ideation and core agent loop definition
- Four-phase architecture: Understand → Explore → Evaluate → Report
- Seven evaluation lenses defined (functionality, design, UX, performance, accessibility, code, content)
- Report structure and tagging system
- Technical architecture options (headless browser, LLM vision, DOM analysis, tool integration)

**Decisions Made:**
1. V1 will be a web app; desktop and mobile planned for later phases
2. V1 will attempt both deep-dive and broad sweep (move fast philosophy)
3. Primary output is structured markdown optimized for AI consumption
4. Agent should have multi-modal output capabilities (text + screenshots) and decide which is most effective per finding
5. Initial personal tool, future paid product as part of a tool suite
6. Target customers: vibe coders, solo developers, students
7. Input interface: text field + file upload (drag/drop/paste) + URL — three channels, plus autonomous context gathering
8. Parent brand is **BaryApps** — a collection of small-to-medium scale apps and tools
9. Competitive positioning is irrelevant to build decision — "if I need it, others who work like me will too"
10. Agent should be capable of comparing uploaded sketches/mockups against live app to identify intent vs. execution gaps
11. BaryApps is a hub/"desktop" — each tool lives independently at its own URL/deployment, BaryApps is the directory
12. User can optionally specify a test route/flow for the agent to follow — app should inform user of this option
13. **Dual-report output:** Report A = AI-consumable (with file paths, CSS selectors, machine-parseable instructions), Report B = human-readable (with screenshots, explanations, context)
14. Existing BaryApps tools will be the first dogfooding targets for this agent
15. Shared infrastructure (auth, billing) integrates later at public launch — V1 ships standalone
16. Tech stack detection: dual approach — agent infers from live app + optional user-provided field
17. V1 Definition of Done established: agent evaluates a BaryApps tool → Report A is handed to coding AI → fixes are correct and actionable
18. Tool named: **GoNoGo** — from the go/no-go launch decision framework. Punchy, memorable, perfectly describes the tool's purpose.
19. Tech stack recommendation delivered: Python/FastAPI backend, Playwright, React+Vite frontend, Redis/Celery job queue, SSE for progress, SQLite→PostgreSQL, local→S3/R2 storage. Awaiting founder review.
20. Agent architecture: **multi-step pipeline** (10 steps), not a single mega-prompt. Each lens gets its own LLM call with tailored inputs and rubric.
21. Evaluation pipeline fully designed: Recon → Intent → Tech Stack → 6 parallel lens evaluations → Synthesis/Scoring → Dual Report Generation
22. Scoring model: per-lens scores (0–100 + letter grade) + overall composite + **GO / NO-GO / GO WITH CONDITIONS** verdict
23. Prompt engineering principles established: structured output, rubric-driven, evidence-required, dual recommendations, persona injection, calibration examples, confidence scoring, self-review
24. Universal finding schema designed: every finding includes evidence anchors (selectors, URLs, screenshots) and dual recommendations (human + AI versions)
25. Report A (AI handoff) designed for zero-ambiguity machine consumption. Report B (human review) designed with screenshots, context, and encouraging tone.
26. File upload broadened: accepts any reference material (mockups, sketches, handwritten notes, spec docs, annotated screenshots), not limited to design files.
27. Autonomous context gathering: agent gathers from URL, website, content, the app itself, and any available sources.
28. **Live progress feed:** Status text via SSE, toggle available (default OFF), negligible cost — no extra LLM calls needed.
29. **Hosting:** Vercel for frontend (GitHub → Vercel deploy), Railway/VPS for backend (persistent processes needed for Playwright).
30. **Authentication:** Credential form per scan (username/password or session token), discarded after use. V1 tests public routes only.
31. **LLM provider:** Gemini API primary (2.5 Pro for design/UX/synthesis/report gen, 2.5 Flash for functionality/performance/a11y/code). Claude API as secondary option ready.
32. **Exploration depth:** Page type mapping — deep-test 1 representative per type, spot-check 2–3 more, shallow-crawl rest. Max 30 deep, 100 shallow, 10 min timeout.
33. **Pricing model:** BYOK primary (users bring own Gemini key). Hosted tier ($2–5/scan) for non-technical users. Subscription option later.
34. **Tech stack approved:** Python/FastAPI, Playwright, React+Vite, Redis/Celery, SQLite→PostgreSQL, local→S3/R2.
35. **Sketch comparison:** Conceptual via LLM vision. Reads text in images (notes, annotations). Not pixel-level.
36. **Agent personality:** Opinionated and direct — like a reliable senior who sincerely wants you to be better. Personality in Report B only.
37. **Scan history:** Yes — ~2–5MB per scan, includes comparison and tracking over time. Low cost.
38. **Report delivery:** Download buttons as primary method.
39. **Prompt version control:** Versioned files in `/prompts/`, tracked per scan record, CHANGELOG.md.
40. **Calibration dataset:** 5 reference sites spanning quality spectrum. Manual ground truth → compare → tune → regression test.
41. **Cost model completed:** ~$0.50/scan average (Gemini API). $0.25–$1.00 range. Personal use at 20 scans/month ≈ $10/month in API costs.
42. **Prompt creation ownership clarified:** AI assistant drafts all prompts. Founder tests and QA's output. Iterate together. Founder does NOT need to write prompts from scratch.
43. **Calibration baseline ownership clarified:** AI assistant creates initial ground truth evaluations for all calibration sites. Founder reviews and approves. AI assistant will proactively remind founder to revisit calibration after prompt changes.

---

## 9. Tool Name: GoNoGo

### Final Decision: **GoNoGo**

**Origin:** From the "go/no-go" decision framework used in aviation, space launches, and mission-critical engineering — the final checkpoint where every system is evaluated before proceeding.

**Why it works:**
- Perfectly describes the tool's purpose: is your app ready to ship, or not?
- Punchy, memorable, easy to say and spell
- Works as a verb: "GoNoGo it before you launch"
- Implies rigor and thoroughness without being intimidating
- Resonates with the builder/maker audience — they're building things and need a launch decision
- Stands strong independently and under the BaryApps umbrella
- Natural CTA: "Run GoNoGo" / "Get your GoNoGo report"

**URL/Branding considerations (TBD):**
- Domain: gonogo.app? gonogo.dev? gonogo.tools? baryapps.com/gonogo?
- Logo direction: could lean into the aviation/launch metaphor (runway, launchpad, green light)

---

*This document will be updated as the project evolves. All major planning questions are now resolved. Next steps: secure domain, set up repo structure, build Step 0 (Recon) as proof of concept, write first prompt drafts for the evaluation pipeline, assemble calibration dataset.*
