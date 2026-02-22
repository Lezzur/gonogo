# GoNoGo Fix Loop — Barker Build Plan

> Feature addition: fully automated scan → Claude Code fix → redeploy → rescan loop. Claude Code is invoked programmatically via headless mode (`claude -p`) — no manual intervention required during the cycle.

```yaml
# ============================================================
# BARKER BUILD PLAN — GoNoGo Fix Loop Integration
# ============================================================
# This is a feature addition to the existing GoNoGo project.
# All existing code is already built and on disk.
# ============================================================

project:
  name: "gonogo"
  description: "Add automated fix loop: scan → Claude Code headless fix → redeploy → rescan cycle"
  working_directory: "."

input_files:
  - path: "GONOGO_BUILD_SPEC.md"
    alias: "spec"
    description: "Full GoNoGo build specification"
  - path: "GONOGO_FIX_LOOP_DECISIONS.md"
    alias: "decisions"
    description: "Design decisions for fix loop feature"

phases:
  # ============================================================
  # PHASE 1: Data Model & Config Extensions
  # ============================================================
  - id: "phase-1"
    name: "Data Model & Config"
    description: "Extend database models, schemas, and config for fix loop"

    tasks:
      - id: "p1-models"
        name: "Extend Scan model and add FixCycle model"
        model: "opus"
        depends_on: []
        estimated_minutes: 15
        context_sources:
          - alias: "spec"
            sections: ["5"]
          - alias: "decisions"
            sections: ["all"]
        prompt: |
          Read backend/models.py and backend/schemas.py to understand the current data model.

          Extend the existing Scan model in backend/models.py:
          - Add `fix_loop_enabled` (Boolean, default False)
          - Add `fix_branch` (String, nullable) — git branch name like "gonogo/fix-<short_id>"
          - Add `max_cycles` (Integer, default 3)
          - Add `stop_on_verdict` (String, default "GO") — "GO", "GO_WITH_CONDITIONS", or "never"
          - Add `current_cycle` (Integer, default 0)
          - Add `parent_scan_id` (String, nullable, ForeignKey to scans.id) — links rescan to original
          - Add `deploy_mode` (String, default "branch") — "branch", "manual", "local"
          - Add `deploy_command` (String, nullable) — user-configured deploy command
          - Add `severity_filter` (JSON, nullable) — which severities to fix, e.g. ["critical", "high"]
          - Add `apply_mode` (String, default "branch") — "branch" or "direct"
          - Add `repo_path` (String, nullable) — path to the target project's git repo on the server

          Create a new FixCycle model in backend/models.py:
          - id (String, primary key, uuid)
          - scan_id (String, ForeignKey to scans.id) — the original scan
          - cycle_number (Integer)
          - rescan_id (String, ForeignKey to scans.id, nullable) — the rescan
          - status (String) — "pending", "fixing", "deploying", "rescanning", "completed", "failed"
          - claude_code_output (Text, nullable) — raw JSON output from Claude Code headless
          - claude_code_cost_usd (Float, nullable) — cost reported by Claude Code
          - claude_code_duration_seconds (Float, nullable)
          - files_modified (JSON, nullable) — list of files Claude Code changed
          - findings_resolved (Integer, default 0)
          - findings_new (Integer, default 0)
          - findings_unchanged (Integer, default 0)
          - created_at (DateTime)
          - completed_at (DateTime, nullable)
          - error_message (Text, nullable)

          Update backend/schemas.py:
          - Add fix loop fields to ScanCreateRequest (fix_loop_enabled, max_cycles, stop_on_verdict, deploy_mode, deploy_command, severity_filter, apply_mode, repo_path)
          - Add FixCycleResponse Pydantic model matching the FixCycle fields above
          - Add FixLoopStartRequest model: repo_path, apply_mode, deploy_mode, deploy_command, max_cycles, stop_on_verdict, severity_filter
          - Add FixLoopStatusResponse: current_cycle, total_cycles, status, cycles (list of FixCycleResponse), fix_branch
          - Update ScanResultResponse to include parent_scan_id, current_cycle, fix_branch

          Run the existing database setup to verify models are valid.
        expected_files:
          - "backend/models.py"
          - "backend/schemas.py"
      - id: "p1-config"
        name: "Add fix loop and Claude Code config"
        model: "sonnet"
        depends_on: []
        estimated_minutes: 5
        context_sources:
          - alias: "spec"
            sections: ["11"]
          - alias: "decisions"
            sections: ["4"]
        prompt: |
          Read backend/config.py and .env.example.

          Add these new config values to backend/config.py:
          - DEFAULT_MAX_CYCLES = int, default 3
          - DEFAULT_STOP_ON_VERDICT = str, default "GO"
          - DEFAULT_DEPLOY_MODE = str, default "branch"
          - DEFAULT_APPLY_MODE = str, default "branch"
          - FIX_BRANCH_PREFIX = str, default "gonogo/fix-"
          - CLAUDE_CODE_PATH = str, default "claude" (path to Claude Code CLI binary)
          - CLAUDE_CODE_MAX_TURNS = int, default 50 (max tool-use turns per fix session)
          - CLAUDE_CODE_TIMEOUT_SECONDS = int, default 600 (10 min timeout per fix session)
          - CLAUDE_CODE_PERMISSION_MODE = str, default "bypassPermissions" — full automation, relies on git branch for safety. Users can set to "acceptEdits" for more caution (but may cause incomplete fixes when Claude Code needs bash commands that aren't pre-approved).
          - CLAUDE_CODE_ALLOWED_TOOLS = str, default "Read,Write,Edit,Bash(npm run *),Bash(npx *),Bash(git diff *),Bash(git status)" — only enforced when permission_mode is NOT bypassPermissions (bypass mode ignores allowedTools)
          - CLAUDE_CODE_MAX_BUDGET_USD = float, default 5.0 (per-cycle budget cap)

          Add corresponding entries to .env.example with comments explaining each.
        expected_files:
          - "backend/config.py"
          - ".env.example"
  # ============================================================
  # PHASE 2: Core Services
  # ============================================================
  - id: "phase-2"
    name: "Core Services"
    description: "Git management, deploy triggering, Claude Code invocation, report feeding"

    tasks:
      - id: "p2-git-service"
        name: "Git branch management service"
        model: "opus"
        depends_on: ["p1-config"]
        estimated_minutes: 20
        context_sources:
          - alias: "decisions"
            sections: ["2", "3"]
        prompt: |
          Create backend/services/git_manager.py — a service that manages git branches for the fix loop.

          Read backend/config.py for the FIX_BRANCH_PREFIX setting.

          Implement a GitManager class with these async methods:
          - `create_fix_branch(repo_path: str, scan_id: str) -> str` — creates and checks out a new branch named "{FIX_BRANCH_PREFIX}{scan_id[:8]}". Returns the branch name. Raises if repo_path is not a git repo.
          - `get_current_branch(repo_path: str) -> str` — returns current branch name.
          - `get_original_branch(repo_path: str) -> str` — returns the branch that was active before the fix branch was created (stored as instance state).
          - `get_diff_summary(repo_path: str, base_branch: str) -> dict` — returns {"files_changed": int, "insertions": int, "deletions": int, "files": [list of changed file paths]}.
          - `commit_fixes(repo_path: str, cycle_number: int) -> str` — stages all changes, commits with message "GoNoGo fix cycle {n}", returns commit hash.
          - `switch_branch(repo_path: str, branch: str) -> None` — checks out the specified branch.
          - `delete_branch(repo_path: str, branch: str) -> None` — deletes the branch (for cleanup on discard).
          - `is_git_repo(repo_path: str) -> bool` — checks if path is a git repo.

          Use asyncio.create_subprocess_exec to run git commands (not a git library — keep it simple).
          Include proper error handling for: not a git repo, dirty working tree, branch already exists.
          Store the original branch name so we can switch back on cleanup.

          Also create backend/services/__init__.py.
        expected_files:
          - "backend/services/__init__.py"
          - "backend/services/git_manager.py"
      - id: "p2-deploy-service"
        name: "Deploy trigger service"
        model: "opus"
        depends_on: ["p1-config"]
        estimated_minutes: 15
        context_sources:
          - alias: "decisions"
            sections: ["3"]
        prompt: |
          Create backend/services/deploy_manager.py — a service that triggers deploys and waits for them to be reachable.

          Read backend/config.py for deploy-related config.

          Implement a DeployManager class with these async methods:
          - `trigger_deploy(deploy_command: str, branch: str, cwd: str, timeout_seconds: int = 300) -> DeployResult` — runs the user-configured deploy command as a subprocess in the given cwd, substituting {branch} placeholder in the command string. Returns a DeployResult with status, stdout, stderr, deploy_url (parsed from stdout if available).
          - `wait_for_url(url: str, timeout_seconds: int = 120, poll_interval: int = 5) -> bool` — polls the URL until it responds with a 2xx status, or times out. Uses httpx for HTTP calls.
          - `detect_deploy_url(stdout: str) -> Optional[str]` — heuristic to extract a deploy/preview URL from command output. Looks for common patterns like "https://*.vercel.app", "https://*.netlify.app", "https://*.railway.app", URLs on their own line, "Preview:" or "URL:" prefixes, etc.

          Define DeployResult as a Pydantic model:
          - status: str ("success", "failed", "timeout")
          - stdout: str
          - stderr: str
          - deploy_url: Optional[str]
          - duration_seconds: float

          Include error handling for: command not found, timeout, non-zero exit.
          For deploy_mode "local", skip deploy entirely and return the configured local URL as deploy_url.
          For deploy_mode "manual", return a DeployResult with status "awaiting_url".
        expected_files:
          - "backend/services/deploy_manager.py"
      - id: "p2-claude-code-service"
        name: "Claude Code headless invocation service"
        model: "opus"
        depends_on: ["p1-config"]
        estimated_minutes: 25
        context_sources:
          - alias: "decisions"
            sections: ["1", "2"]
        prompt: |
          Create backend/services/claude_code.py — the service that invokes Claude Code in headless mode to apply fixes from a GoNoGo report.

          Read backend/config.py for all CLAUDE_CODE_* settings.

          This is the core automation piece. GoNoGo invokes Claude Code as a subprocess, passes it the filtered Report A, and Claude Code modifies files in the target repo autonomously.

          Implement a ClaudeCodeRunner class:

          __init__(self, config):
            Store config values: claude_code_path, max_turns, timeout, permission_mode, allowed_tools, max_budget_usd.

          async check_installed(self) -> tuple[bool, str]:
            Check if the claude binary exists and is executable.
            Run `claude --version` to verify. Return (True, version_string) or (False, error_message).

          async run_fixes(self, repo_path: str, report_content: str, cycle_number: int, tech_stack: str = "") -> ClaudeCodeResult:
            1. Write the report content to a temp file at {repo_path}/.gonogo-report-cycle-{n}.md
               (Claude Code can then read it from the working directory — avoids large stdin issues)
            2. Construct the Claude Code command as a list of args:
               [
                 self.claude_code_path, "-p",
                 "--cwd", repo_path,
                 "--permission-mode", self.permission_mode,
                 "--allowedTools", self.allowed_tools,
                 "--output-format", "json",
                 "--max-turns", str(self.max_turns),
                 "--max-budget-usd", str(self.max_budget_usd),
               ]
            3. The prompt (passed as the positional arg after -p or piped):
               "Read the GoNoGo QA report at .gonogo-report-cycle-{n}.md in this project directory. It contains findings from an automated quality audit of this codebase, organized by severity. Fix every finding listed, starting with Critical, then High, then Medium, then Low. For each finding: read the relevant source files, understand the issue described, and implement the fix as specified in the 'Fix' instruction. After all fixes are applied, list every file you modified."
               If tech_stack is provided, append: "This project uses: {tech_stack}"
            4. Run via asyncio.create_subprocess_exec with the configured timeout.
            5. Parse the JSON output. Expected structure:
               {"type": "result", "subtype": "success"|"error", "result": "...", "total_cost_usd": 0.xx, "duration_ms": ..., "session_id": "...", "is_error": bool}
            6. Extract the list of modified files from the result text (Claude Code will list them).
            7. Clean up the temp .gonogo-report-cycle-{n}.md file.
            8. Return a ClaudeCodeResult.

          Define ClaudeCodeResult as a Pydantic model:
          - status: str ("success", "error", "timeout")
          - result_text: str — Claude Code's summary of what it did
          - cost_usd: float
          - duration_seconds: float
          - session_id: Optional[str]
          - files_modified: List[str]
          - error_message: Optional[str]
          - raw_output: str — full JSON output for debugging

          Error handling:
          - Timeout: kill the subprocess tree, return status "timeout"
          - Non-zero exit: capture stderr, return status "error"
          - Claude Code not installed: raise clear error before attempting
          - JSON parse failure: store raw stdout, return status "error"
          - Auth failure (look for "not authenticated" in output): specific error message

          IMPORTANT: Do NOT pipe the report via stdin. There is a known Claude Code bug where
          large stdin inputs (7k+ chars) produce empty output. Write the report to a file in
          the repo directory and reference it in the prompt. This is reliable at any size.

          IMPORTANT: The permission_mode is user-configurable:
          - "bypassPermissions" (default): Full automation. Claude Code can run any operation
            without prompting. This is the recommended default because acceptEdits will cause
            Claude Code to stall on bash commands it needs (npm install, mkdir, rm, build commands)
            and the headless session has no one to approve. The git branch provides the safety net.
          - "acceptEdits": More cautious — auto-approves file edits but blocks bash commands
            that aren't in the allowedTools list. May result in incomplete fixes. Use when
            apply_mode is "direct" (no git branch safety net) or in sensitive environments.
          
          When permission_mode is "bypassPermissions", --allowedTools is ignored by Claude Code.
          When permission_mode is "acceptEdits", --allowedTools scopes what bash commands are
          auto-approved. Default allowedTools permits file ops and safe build commands but blocks
          rm -rf, git push, sudo, etc.
        expected_files:
          - "backend/services/claude_code.py"
      - id: "p2-report-feed"
        name: "Report feed and severity filtering"
        model: "sonnet"
        depends_on: ["p1-models"]
        estimated_minutes: 10
        context_sources:
          - alias: "decisions"
            sections: ["1"]
          - alias: "spec"
            sections: ["10"]
        prompt: |
          Create backend/services/report_feed.py — a service that prepares Report A for consumption by Claude Code, with severity filtering.

          Read backend/scanner/report_gen.py and backend/schemas.py to understand the current report structure and Finding schema.

          Implement:
          - `filter_report_by_severity(report_a_path: str, severities: List[str]) -> str` — reads the full Report A markdown, parses it by severity sections (CRITICAL, HIGH PRIORITY, MEDIUM PRIORITY, LOW PRIORITY), returns only the sections matching the requested severities. Always includes the header (verdict, score, tech stack, date).
          - `estimate_token_count(text: str) -> int` — rough estimate: len(text) / 4.
          - `prepare_feed(report_a_path: str, severities: List[str]) -> str` — filters report by severity and returns as a single string.
          - `generate_delta_report(current_findings: List[dict], previous_findings: List[dict]) -> dict` — compares findings between two scans by finding ID. Returns {"resolved": [...], "new": [...], "unchanged": [...], "resolved_count": int, "new_count": int, "unchanged_count": int}.
        expected_files:
          - "backend/services/report_feed.py"
  # ============================================================
  # PHASE 3: Fix Loop Orchestrator
  # ============================================================
  - id: "phase-3"
    name: "Fix Loop Orchestrator"
    description: "The core automated loop that ties everything together"

    tasks:
      - id: "p3-fix-loop-orchestrator"
        name: "Fix loop orchestrator — the automated cycle"
        model: "opus"
        depends_on: ["p1-models", "p2-git-service", "p2-deploy-service", "p2-claude-code-service", "p2-report-feed"]
        estimated_minutes: 30
        context_sources:
          - alias: "decisions"
            sections: ["all"]
          - alias: "spec"
            sections: ["6", "8"]
        prompt: |
          Create backend/scanner/fix_loop.py — the main orchestrator for the fully automated scan→fix→redeploy→rescan cycle.

          Read these existing files first:
          - backend/scanner/orchestrator.py (the existing scan orchestrator — you will call run_scan for rescans)
          - backend/services/git_manager.py
          - backend/services/deploy_manager.py
          - backend/services/claude_code.py
          - backend/services/report_feed.py
          - backend/utils/progress.py (for SSE broadcasting)
          - backend/models.py and backend/schemas.py (for data models)
          - backend/database.py (for DB session management)

          Implement a FixLoopOrchestrator class:

          __init__(self, scan_id: str, config: FixLoopStartRequest, db_session):
            Store references. Initialize GitManager, DeployManager, ClaudeCodeRunner.
            Load the original scan from DB. Validate it is completed and has a report_a_path.

          async run(self) -> None:
            This is the FULLY AUTOMATED loop. Once started, it runs to completion without
            human intervention (except deploy_mode="manual" which needs user to provide URL).

            1. Load original scan. Get report_a_path, tech_stack_detected, url.
            2. If apply_mode == "branch":
               - Call git_manager.create_fix_branch(repo_path, scan_id)
               - Store branch name in scan record
            3. Initialize: current_report_path = original report_a_path
            4. For cycle_number in 1..max_cycles:
               a. Check stop_requested flag (set by stop endpoint). If true, break.
               b. Create FixCycle record (status: "fixing")
               c. Broadcast: "Cycle {n}/{max}: Preparing report for Claude Code..."
               d. filtered_report = report_feed.prepare_feed(current_report_path, severity_filter)
               e. Broadcast: "Cycle {n}/{max}: Claude Code is fixing issues... (this may take several minutes)"
               f. result = claude_code_runner.run_fixes(repo_path, filtered_report, cycle_number, tech_stack)
               g. Update FixCycle: claude_code_output, cost, duration, files_modified, status
               h. If result.status != "success": set cycle "failed", broadcast error, break
               i. If apply_mode == "branch": git_manager.commit_fixes(repo_path, cycle_number)
               j. Broadcast: "Cycle {n}/{max}: Deploying fixed version..."
               k. Handle deploy:
                  - "branch": deploy_manager.trigger_deploy(deploy_command, fix_branch, repo_path)
                  - "local": skip deploy, use original URL (dev server auto-reloads on file change)
                  - "manual": broadcast "awaiting_deploy_url", wait on asyncio.Event for advance()
               l. If deploy failed: set cycle "deploy_failed", broadcast error, break
               m. rescan_url = deploy_result.deploy_url or original url
               n. deploy_manager.wait_for_url(rescan_url) — wait for it to be reachable
               o. Broadcast: "Cycle {n}/{max}: Rescanning to verify fixes..."
               p. Run rescan: create a new scan via orchestrator.run_scan(rescan_url, ...)
                  - Set parent_scan_id on the new scan
                  - Use same api_key and llm_provider as original
               q. delta = report_feed.generate_delta_report(new_findings, previous_findings)
               r. Update FixCycle: rescan_id, findings_resolved/new/unchanged, status="completed"
               s. Broadcast delta: "{resolved} fixed, {new} new, {unchanged} unchanged. Score: {old}→{new}"
               t. current_report_path = new scan's report_a_path (for NEXT cycle)
               u. Check stop condition:
                  - If stop_on_verdict != "never" AND rescan verdict matches: break with success message
               v. Continue to next cycle
            5. Broadcast completion summary: total cycles, total resolved, original→final score/verdict, total cost
            6. If apply_mode == "branch": broadcast "Review and merge branch: {fix_branch}"

          async advance(self, deploy_url: str):
            For deploy_mode="manual" only. Sets the deploy_url and signals the asyncio.Event.

          stop_requested: bool flag, checked between cycles.

          async request_stop(self):
            Sets stop_requested = True. Current cycle finishes, then loop exits.
        expected_files:
          - "backend/scanner/fix_loop.py"
  # ============================================================
  # PHASE 4: API Endpoints
  # ============================================================
  - id: "phase-4"
    name: "API Endpoints"
    description: "REST endpoints for fix loop control"

    tasks:
      - id: "p4-api"
        name: "Fix loop API endpoints"
        model: "opus"
        depends_on: ["p3-fix-loop-orchestrator"]
        estimated_minutes: 20
        context_sources:
          - alias: "spec"
            sections: ["6"]
          - alias: "decisions"
            sections: ["1", "2", "3", "4"]
        prompt: |
          Read the existing backend/api/scans.py and backend/api/reports.py for API patterns.
          Read backend/scanner/fix_loop.py and backend/schemas.py.

          Create backend/api/fix_loop.py with a new APIRouter:

          POST /api/scans/{scan_id}/fix-loop
            Start automated fix loop. Body: FixLoopStartRequest.
            Validates: scan completed, has report, no active loop, Claude Code installed.
            Launches FixLoopOrchestrator as background task.
            Returns: { fix_loop_id, status: "started", fix_branch, estimated_cycles }

          GET /api/scans/{scan_id}/fix-loop/stream
            SSE for real-time progress. Events: cycle_start, fixing, deploying, rescanning,
            cycle_complete (with delta), loop_complete, error, awaiting_deploy_url.

          GET /api/scans/{scan_id}/fix-loop/status
            Current state: cycle, status, all FixCycle records with costs/deltas/files.
            Totals: cost, findings_resolved, time elapsed.

          POST /api/scans/{scan_id}/fix-loop/advance
            For deploy_mode="manual" only. Body: { deploy_url: str }

          GET /api/scans/{scan_id}/fix-loop/diff
            Git diff summary (apply_mode="branch" only).

          POST /api/scans/{scan_id}/fix-loop/stop
            Stop after current cycle.

          GET /api/scans/{scan_id}/fix-loop/check-prerequisites
            Pre-flight: Claude Code installed? Repo path valid? Git repo (if branch mode)?
            Query params: repo_path, apply_mode.
            Returns: { ready: bool, issues: List[str] }

          Register in backend/main.py.
        expected_files:
          - "backend/api/fix_loop.py"
          - "backend/main.py"
  # ============================================================
  # PHASE 5: Frontend
  # ============================================================
  - id: "phase-5"
    name: "Frontend UI"
    description: "Fix loop controls, progress, and cycle visualization"

    tasks:
      - id: "p5-api-client"
        name: "Frontend API client extensions"
        model: "sonnet"
        depends_on: ["p4-api"]
        estimated_minutes: 8
        context_sources:
          - alias: "decisions"
            sections: ["all"]
        prompt: |
          Read frontend/src/api/client.ts for existing patterns.

          Add functions: checkFixLoopPrerequisites, startFixLoop, getFixLoopStatus,
          advanceFixLoop, getFixDiff, stopFixLoop, streamFixLoopProgress (SSE).

          Define TypeScript interfaces: FixLoopStartRequest, FixLoopStartResponse,
          FixLoopStatusResponse, PrerequisiteCheckResponse, DiffResponse, StopResponse,
          FixCycleInfo (with claude_code_cost_usd, files_modified, delta counts, etc.),
          FixLoopEvent.
        expected_files:
          - "frontend/src/api/client.ts"
      - id: "p5-fix-loop-config"
        name: "Fix loop configuration panel"
        model: "sonnet"
        depends_on: ["p5-api-client"]
        estimated_minutes: 15
        context_sources:
          - alias: "decisions"
            sections: ["1", "2", "3", "4"]
        prompt: |
          Read frontend/src/components/ScanResults.tsx and frontend/src/api/client.ts.

          Create frontend/src/components/FixLoopConfig.tsx — config panel shown after scan completes.

          Header: "Automated Fix Loop" / "Claude Code will fix issues, redeploy, and rescan automatically."

          Fields:
          1. Repository Path (required) + "Check" button calling checkFixLoopPrerequisites. Show green/red result inline.
          2. Apply Mode toggle: "Git Branch" (default) | "Direct Edits" with appropriate helper/warning text.
          3. Permission Mode toggle: "Full Automation" (default, bypassPermissions) | "Cautious (acceptEdits)"
             - Full Automation: helper text "Claude Code can run any operation. Git branch provides safety."
             - Cautious: helper text "Claude Code can edit files freely but needs approval for bash commands. May result in incomplete fixes if Claude Code needs to run install/build commands."
             - If apply_mode is "Direct Edits" AND permission_mode is "Full Automation", show warning:
               "⚠ Full automation without git branch means no rollback. Consider switching to Git Branch mode or Cautious permissions."
          4. Severity Filter: checkboxes for Critical (default on), High (default on), Medium, Low.
          5. Deploy Mode select: "Preview Deploy" | "Local Dev Server" | "Manual"
             - Preview: show deploy command input, placeholder "vercel deploy --branch {branch}"
             - Local: show URL input, default "http://localhost:3000"
             - Manual: explanatory text
          6. Max Cycles: number 1-10, default 3.
          7. Stop Condition select: "Stop on GO" (default) | "Stop on GO WITH CONDITIONS" | "Manual stop only"

          CTA: "Start Automated Fix Loop"
          Below: "Estimated cost: ~$2-5 per cycle."

          On submit: validate, call startFixLoop, emit callback to parent to switch to progress view.
          Tailwind CSS, match ScanForm.tsx styling.
        expected_files:
          - "frontend/src/components/FixLoopConfig.tsx"
      - id: "p5-fix-loop-progress"
        name: "Fix loop progress and cycle display"
        model: "sonnet"
        depends_on: ["p5-api-client"]
        estimated_minutes: 20
        context_sources:
          - alias: "decisions"
            sections: ["all"]
        prompt: |
          Read frontend/src/components/ScanProgress.tsx for SSE pattern.
          Read frontend/src/api/client.ts for fix loop types.

          Create frontend/src/components/FixLoopProgress.tsx — live display of the automated loop.

          1. Cycle progress bar: circles showing completed/active/remaining cycles.
          2. Live status: large pulsing text ("Cycle 2/3: Claude Code is fixing 7 issues...")
          3. Cycle history cards (stack as each completes):
             - Delta: "✓ 8 fixed | ⚠ 1 new | — 3 unchanged"
             - Score delta: "52 → 74 (+22)"
             - Cost: "$1.23" | Duration: "3m 42s"
             - Files modified: expandable list
             - Link to rescan results
          4. Manual deploy prompt (only when awaiting_deploy_url): URL input + Continue button.
          5. Running totals: findings resolved, total cost, elapsed time, original→current verdict/score.
          6. Controls: "Stop After Current Cycle" button, "View Branch Diff" button (branch mode only).
          7. Completion state: verdict reached / max cycles hit / user stopped / error.
             If branch mode: "Review and merge branch gonogo/fix-abc123"

          SSE via streamFixLoopProgress(). Tailwind CSS.
        expected_files:
          - "frontend/src/components/FixLoopProgress.tsx"
      - id: "p5-wire-pages"
        name: "Wire fix loop into existing pages"
        model: "sonnet"
        depends_on: ["p5-fix-loop-config", "p5-fix-loop-progress"]
        estimated_minutes: 10
        prompt: |
          Read: frontend/src/pages/ScanPage.tsx, frontend/src/components/ScanResults.tsx,
          frontend/src/components/ScanHistory.tsx, frontend/src/App.tsx.

          Changes:
          1. ScanResults.tsx: Add FixLoopConfig after download buttons. Show when scan completed
             with findings. Add fixLoopActive state — when true, render FixLoopProgress instead.
          2. ScanPage.tsx: Handle transition ScanResults ↔ FixLoopProgress. On loop complete,
             reload scan data to show latest rescan results.
          3. ScanHistory.tsx: Show "Fix Loop Cycle N" badge on rescans (parent_scan_id set).
             Group under parent. Show score delta.
          4. App.tsx: No new routes. Verify existing routing works.
        expected_files:
          - "frontend/src/pages/ScanPage.tsx"
          - "frontend/src/components/ScanResults.tsx"
          - "frontend/src/components/ScanHistory.tsx"
  # ============================================================
  # PHASE 6: Delta Reporting
  # ============================================================
  - id: "phase-6"
    name: "Delta Reporting"
    description: "Delta sections in rescan reports"

    tasks:
      - id: "p6-delta-report"
        name: "Delta section in Reports A and B"
        model: "opus"
        depends_on: ["p2-report-feed"]
        estimated_minutes: 15
        context_sources:
          - alias: "spec"
            sections: ["10"]
          - alias: "decisions"
            sections: ["5"]
        prompt: |
          Read backend/scanner/report_gen.py and backend/services/report_feed.py.

          Modify report_gen.py: when generating a report with parent_scan_id, add a Delta
          section after the header in both reports.

          Report A delta:
          ## DELTA FROM PREVIOUS SCAN (Cycle {n})
          - Findings resolved: {count} ({IDs})
          - New findings: {count} ({IDs})
          - Unchanged: {count}
          - Score: {old} → {new} ({+/-delta})

          Report B delta:
          ### Changes Since Last Scan (Cycle {n})
          **Resolved ({count})** with strikethrough finding titles
          **New Issues ({count})** with warning flags
          **Still Open ({count})**
          **Score:** {old} → {new} ({+/-delta})

          Accept optional params: delta_data, cycle_number, previous_score.
          When absent (normal scan), skip delta section entirely.
        expected_files:
          - "backend/scanner/report_gen.py"
  # ============================================================
  # PHASE 7: Error Handling
  # ============================================================
  - id: "phase-7"
    name: "Error Handling"
    description: "Comprehensive error handling and edge cases"

    tasks:
      - id: "p7-error-handling"
        name: "Backend error handling"
        model: "opus"
        depends_on: ["p4-api", "p6-delta-report", "p2-git-service", "p2-deploy-service", "p2-claude-code-service", "p3-fix-loop-orchestrator"]
        estimated_minutes: 15
        context_sources:
          - alias: "decisions"
            sections: ["all"]
        prompt: |
          Read all fix loop backend files: fix_loop.py, api/fix_loop.py, git_manager.py,
          deploy_manager.py, claude_code.py, report_feed.py.

          Add error handling for:
          1. Claude Code not installed → clear install instructions
          2. Claude Code auth failure → "Run 'claude /login' on server"
          3. Git: not a repo → suggest direct mode. Dirty tree → error. Branch exists → suffix counter
          4. Deploy: cmd not found, timeout, non-zero → "deploy_failed", broadcast with stderr
          5. Rescan failure → "rescan_failed", store partial results
          6. Budget exceeded → Claude Code self-terminates, log warning
          7. Concurrent loops → prevent in POST endpoint
          8. Server restart → mark interrupted cycles, don't auto-resume
          9. Cleanup → remove .gonogo-report-cycle-*.md temp files after loop ends

          Wrap subprocess calls in try/except. Log everything.
        expected_files:
          - "backend/scanner/fix_loop.py"
          - "backend/api/fix_loop.py"
          - "backend/services/git_manager.py"
          - "backend/services/deploy_manager.py"
          - "backend/services/claude_code.py"
      - id: "p7-frontend-errors"
        name: "Frontend error states"
        model: "sonnet"
        depends_on: ["p5-wire-pages", "p5-fix-loop-config", "p5-fix-loop-progress"]
        estimated_minutes: 10
        prompt: |
          Read FixLoopProgress.tsx and FixLoopConfig.tsx.

          Add: prerequisite check failures inline, start failure banner, Claude Code failure
          display, deploy failure with stderr + manual URL fallback, rescan failure, SSE
          reconnect with backoff, completed-cycles summary always visible on error.
          Tailwind. Clear, actionable error messages.
        expected_files:
          - "frontend/src/components/FixLoopProgress.tsx"
          - "frontend/src/components/FixLoopConfig.tsx"
  # ============================================================
  # PHASE 8: Documentation
  # ============================================================
  - id: "phase-8"
    name: "Documentation"
    description: "Update project docs"

    tasks:
      - id: "p8-docs"
        name: "Update project documentation"
        model: "sonnet"
        depends_on: ["p7-error-handling", "p7-frontend-errors"]
        estimated_minutes: 10
        context_sources:
          - alias: "decisions"
            sections: ["6"]
        prompt: |
          Read and update GONOGO_BUILD_SPEC.md, GONOGO_PLANNING_DOC.md, README.md.

          BUILD_SPEC: Add §14 Fix Loop Integration covering: Claude Code headless integration
          (how invoked, permissions, budget, allowed tools), report feed via file (not stdin),
          git branch strategy, deploy pipeline, cycle config, delta reporting, new API endpoints,
          new models, new config, prerequisites. Update TOC and repo structure.

          PLANNING_DOC: Add resolved decisions to §7 (report feed, git branch, deploy,
          cycles, Claude Code integration approach). Add conversation log entry.

          README: Add "Automated Fix Loop" section: overview, prerequisites (Claude Code installed),
          usage flow, git branch safety note.
        expected_files:
          - "GONOGO_BUILD_SPEC.md"
          - "GONOGO_PLANNING_DOC.md"
          - "README.md"
```

---

## Human-Readable Summary

### What This Does

GoNoGo scans your app, produces a report, then **automatically invokes Claude Code to fix every finding**, commits the fixes to a git branch, deploys a preview, rescans to verify, and repeats until the verdict hits GO. The user watches via SSE and merges when satisfied.

The previous version of this plan had GoNoGo pause and wait for the user to manually copy-paste the report. That's not a loop. This version invokes Claude Code directly via `claude -p` (headless mode) as a subprocess. Fully automated.

### Claude Code Integration Pattern

```bash
claude -p \
  --cwd /path/to/project \
  --permission-mode bypassPermissions \
  --output-format json \
  --max-turns 50 \
  --max-budget-usd 5.0 \
  "Read the GoNoGo QA report at .gonogo-report-cycle-1.md and fix every finding..."
```

Report is written to a file in the repo (not piped via stdin — known bug with large inputs). Claude Code reads it, fixes files, and returns a JSON result with cost and session metadata.

Permission mode is user-toggleable: `bypassPermissions` (default, full automation) or `acceptEdits` (cautious, may stall on bash commands). The default is bypass because `acceptEdits` causes ~20-40% of fix cycles to produce incomplete results — Claude Code needs bash commands (npm install, mkdir, build) that `acceptEdits` blocks in headless mode. The git branch provides the safety net instead.

### Dependency Graph

```
Phase 1: Data Model & Config
  p1-models ──────────────────┐
  p1-config ─────┐            │
                  │            │
Phase 2: Core Services         │
  p2-git-service ◄┘           │
  p2-deploy-service ◄─────────┘
  p2-claude-code-service ◄────┘  ← the key new piece
  p2-report-feed ◄────────────┘
         │  │  │  │
Phase 3: Orchestrator
  p3-fix-loop ◄── ALL Phase 2
                  │
Phase 4: API ◄── p3
                  │
Phase 5: Frontend ◄── p4
  (config + progress parallel, then wire)

Phase 6: Delta Reporting ◄── p2-report-feed (parallel with Phase 5)

Phase 7: Error Handling ◄── p4 + p5 + p6

Phase 8: Docs ◄── p7
```

### Model Split: 8 Opus (50%) / 8 Sonnet (50%)

Higher Opus than typical — justified by subprocess orchestration, state machines, and security-sensitive tool invocation.

### Estimated Time

Critical path: **~2.2 hours**. Total with parallelism: **~3.9 hours**.

### Prerequisites

1. Claude Code CLI: `npm install -g @anthropic-ai/claude-code`
2. Claude Code authenticated: `claude /login` on the server
3. Git installed
4. Target project accessible from server filesystem
