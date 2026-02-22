# GoNoGo — Roadmap & Future Reference

> Last updated: 2026-02-22
> This document captures all discussed features, decisions, and plans for future sessions.

---

## Current State (V1 — Shipped)

### Web App (Vercel + Railway)
- **Scanning**: Crawls sites with Playwright, evaluates 7 quality lenses via AI (Gemini/Claude), returns GO/NO-GO/GO_WITH_CONDITIONS verdict
- **Reports**: Report A (AI Handoff) and Report B (Full Review) downloadable
- **Fix Loop UI**: Full config form (apply mode, permissions, deploy mode, severity filter, max cycles, stop condition)
- **Fix Loop Runtime**: Only works with local backend — requires filesystem access to repo
- **Settings**: API key, LLM provider, fix loop defaults, scan defaults — persisted to localStorage
- **Instructions Page**: User-facing docs on scanning and fix loop setup
- **Auth Detection**: Warns user if site requires login but no credentials provided
- **History**: Scan history with comparison capability

### Known Limitations
- Fix loop does not work on production (Railway) — backend cannot access user's local repo
- Railway free tier has ~$4.99 remaining — limited compute
- `networkidle` timeout on busy sites — mitigated with `domcontentloaded` fallback
- SQLite on Railway ephemeral filesystem — data lost on redeploy if no volume

---

## V2 — CLI with TUI

### Why TUI over other options
- **vs Tauri/Electron**: Lighter, no 300-500MB bundle, no Rust/packaging complexity
- **vs plain CLI**: Visual feedback — progress bars, score cards, interactive forms
- **vs web-only**: Fix loop works natively (local filesystem access), no "local backend" workaround needed
- **Tech**: Textual (Python) — same language as backend, imports scanner directly, no HTTP layer

### TUI Features to Build

#### Core Screens
1. **Home/Menu** — Interactive mode: scan, history, settings, fix loop
2. **Scan Screen** — URL input, progress bar with step indicators, live status
3. **Results Screen** — Verdict badge (colored), score circle, findings grid, top 3 actions
4. **Fix Loop Screen** — Config form (all current options), cycle progress, diff viewer
5. **History Screen** — Table of past scans, select to view details
6. **Settings Screen** — Interactive form mirroring web settings page

#### Config & Settings
- Stored in `~/.gonogo/config.json` (not localStorage)
- **Reports save path** — configurable directory for where reports are saved to disk (default: `~/gonogo-reports/`)
- **Default repo path** — pre-fills fix loop repo field
- **API keys** — Gemini key, Anthropic key (or Claude login auth)
- **LLM provider default** — gemini or claude
- **All fix loop defaults** — same as web settings (apply mode, permissions, deploy mode, severity, max cycles, stop condition)

#### Tip Line
- Persistent footer bar showing rotating tips/reminders
- Two categories:
  - **User tips**: "Press F to start fix loop", "Use --json flag for CI output", "Set default repo path in settings to skip typing it each time"
  - **Builder reminders**: "Next up: remote-clone capability", "Consider adding GitHub Actions integration", "Textual supports mouse — add click targets", "Add --watch mode for continuous scanning"
- Tips rotate every 10-15 seconds
- Can be dismissed or hidden via settings

#### CLI Entry Points
```
gonogo                          # Interactive TUI mode
gonogo scan <url>               # Quick scan, show results in TUI
gonogo scan <url> --json        # JSON output for CI/CD
gonogo fix <repo-path>          # Run fix loop on last scan
gonogo history                  # Show past scans
gonogo settings                 # Open settings editor
gonogo login                    # Authenticate Claude Code
```

#### Distribution
- `pip install gonogo` — Python package
- Optional: PyInstaller single binary for zero-dependency install
- Optional: `npx gonogo` wrapper that bootstraps Python

### Build Effort
- Moderate: 3-4 focused sessions
- Backend logic is 100% reusable — only building presentation layer
- Textual has built-in widgets for tables, forms, progress bars, tabs

---

## V2.5 — Remote Fix Loop (Server-Side)

### What it solves
Fix loop works from the web app without local backend setup.

### How it works
1. User provides GitHub repo URL + Personal Access Token
2. Backend clones repo into temp directory on server
3. Claude Code runs fixes on the cloned repo
4. Backend pushes fix branch to GitHub
5. Temp directory cleaned up after loop completes

### Blockers (Concrete)

| Blocker | Detail | Effort |
|---|---|---|
| **Compute budget** | Railway at $4.99. Cloning + Claude Code is CPU/memory heavy | Upgrade plan (~$20/mo) or switch to VPS |
| **Disk storage** | Ephemeral filesystem — repos vanish on redeploy | Add Railway volume ($0.25/GB/mo) or use temp dirs |
| **GitHub auth** | Need to clone private repos | Add PAT field in UI — ~30 min |
| **Claude Code in Docker** | Not installed in current image | `RUN npm install -g @anthropic-ai/claude-code` — trivial |
| **Claude Code auth** | Needs Anthropic key on server | Pass user's key as env var to subprocess — easy |
| **Security** | Code execution on shared server | Isolated temp dirs, timeouts, cleanup. Moderate risk |
| **Concurrency** | Multiple users running fix loops | Queue system or lock. Moderate work |

### No new tech, subscriptions, or LLMs required
Pure infrastructure + engineering. ~2-3 days of focused work once compute budget is addressed.

---

## V3 — Future Features

### Desktop App (Tauri)
- Wrap existing React frontend + Python backend
- Native installer (.exe / .dmg)
- Fix loop works out of the box
- Auto-updates
- Challenge: bundling Python + Playwright (~300-500MB)
- Target audience: non-technical users, agencies

### CI/CD Integration
- GitHub Action: `uses: gonogo/scan@v1` in workflow YAML
- Runs scan on every PR, posts results as PR comment
- Fails pipeline if verdict is NO-GO
- Natural extension of CLI `--json` output

### CLI Tool (npm)
- `npx gonogo scan https://mysite.com`
- Lightweight wrapper that calls Python backend
- Useful for quick checks without TUI

### Enhanced Scanning
- Multiple page scan profiles (mobile, tablet, desktop)
- Scheduled recurring scans
- Scan comparison over time (regression detection)
- Custom lens plugins (user-defined evaluation criteria)

### Fix Loop Improvements
- Support for multiple LLM providers for fix step (not just Claude Code)
- Cost tracking per cycle with actual provider pricing
- Rollback UI — one-click revert a fix cycle
- PR creation — auto-create GitHub PR from fix branch

---

## Decisions Log

| Date | Decision | Rationale |
|---|---|---|
| 2026-02-22 | Textual (Python) for TUI over Ink (React) | Same language as backend, no HTTP layer needed, direct imports |
| 2026-02-22 | CLI+TUI before desktop app | Ships faster, fits developer audience, fix loop works naturally |
| 2026-02-22 | Remote-clone deferred to V2.5 | Railway budget, security concerns, compute limits |
| 2026-02-22 | Fix loop hidden on production web app | Cannot access user's filesystem from Railway |
| 2026-02-22 | Cost estimate removed from fix loop | Actual cost depends on provider; user will add back with real data |
| 2026-02-22 | Settings stored in localStorage (web) | No backend changes needed, simple persistence |
| 2026-02-22 | Auth wall detection added | Users scanning protected sites without credentials need clear feedback |
| 2026-02-22 | domcontentloaded as primary navigation strategy | networkidle never fires on busy sites (GitHub, SPAs with polling) |
| 2026-02-22 | Auto-migrate SQLite columns | Prevents 500 errors when schema evolves without Alembic |

---

## Session Notes

### 2026-02-22 — Settings Page + Deployment Fixes
- Created SettingsContext + SettingsPage (3 sections: API, Fix Loop, Scan Defaults)
- Fixed CORS on Railway (env var needed Deploy click to apply)
- Fixed SQLite missing columns (auto-migration)
- Fixed Playwright Docker image version mismatch (v1.40 -> v1.58)
- Fixed prompt templates not copied to Docker image
- Fixed page.goto timeout on busy sites
- Added auth wall detection + warnings
- Added Instructions page
- Added fix loop local-only notice on production
- Removed cost estimate from fix loop
- Improved scan-not-found error page
