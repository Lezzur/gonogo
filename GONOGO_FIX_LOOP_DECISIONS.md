# GoNoGo → Claude Code Fix Loop: Design Decisions

> Answers to open questions about how GoNoGo reports get consumed, how fixes get applied, and how the scan→fix→rescan cycle works.

---

## 1. Full Feed vs. Batched Feed

**Decision: Tiered feed, user-controlled.**

The report is always *generated* in full. The question is how it's *served* to Claude Code for fixing.

**How it works:**

- GoNoGo produces the complete Report A as it does today — all findings, all severities, sorted by priority.
- If the report is under ~200k tokens (which it almost always will be for V1 sites — a typical Report A is 5–15k tokens), feed the whole thing. Claude Code gets full context and can reason about interdependencies between fixes.
- If the report exceeds ~200k tokens (very large sites, unlikely in V1), batch by severity tier: Critical → High → Medium → Low. GoNoGo tracks which tiers have been fed and processed before allowing a rescan.

**But regardless of feed size, the user chooses which severity tiers to fix.** After viewing the report summary (verdict, scores, top 3 actions, findings count by severity), the user selects:

- "Fix Critical only"
- "Fix Critical + High"
- "Fix Critical + High + Medium"
- "Fix all"

This is the right UX because: the user knows their launch timeline, their risk tolerance, and whether they're doing a quick pre-launch sweep or a thorough quality pass. GoNoGo shouldn't decide that for them.

**Implementation note:** Report A already groups findings by severity. The "tier selection" filters which sections get fed to Claude Code. GoNoGo writes the filtered report to a temp file in the repo (`.gonogo-report-cycle-{n}.md`), then invokes Claude Code headless via `claude -p --cwd {repo} ...` with a prompt that tells it to read and fix everything in that file. The report is passed as a file rather than piped via stdin due to a known Claude Code bug with large stdin inputs.

**Claude Code invocation:** GoNoGo invokes Claude Code directly as a subprocess — this is fully automated, not a manual copy-paste step. The command:
```bash
claude -p \
  --cwd /path/to/project \
  --permission-mode bypassPermissions \
  --allowedTools "Read,Write,Edit,Bash(npm run *),Bash(npx *)" \
  --output-format json \
  --max-turns 50 \
  --max-budget-usd 5.0 \
  "Read the GoNoGo QA report at .gonogo-report-cycle-1.md and fix every finding..."
```
Claude Code returns structured JSON with cost, duration, session ID, and a summary of changes. GoNoGo parses this and proceeds to the deploy+rescan step.

---

## 2. What If Claude Code Breaks Something While Fixing Something Else?

**Decision: Git branch by default. User chooses merge strategy.**

Two options, presented to the user:

### Option A: Direct Local Edits (modify files in place)

| Argument For | Argument Against |
|---|---|
| Zero git overhead — just works | No safety net if a fix breaks something |
| Fastest path for solo devs who are iterating rapidly | Can't easily diff "before GoNoGo" vs. "after GoNoGo" |
| Natural for vibe coders who commit infrequently | If Claude Code introduces a regression, rollback is manual |
| Good for early prototypes where nothing is precious | Dangerous on anything approaching production-ready |

### Option B: Git Branch (recommended default)

| Argument For | Argument Against |
|---|---|
| Full rollback capability — discard the branch if fixes are bad | Requires the project to be a git repo (most are) |
| User can review the diff before merging | Slightly more friction — user must merge or cherry-pick |
| Enables selective merging — accept some fixes, reject others | Branch conflicts possible if user is also actively editing |
| Natural fit with GoNoGo's rescan loop — branch = "fix attempt," merge = "accepted" | Adds a step to the workflow |
| Audit trail — you can see exactly what GoNoGo/Claude Code changed | |

**Default: Option B (Git Branch).** GoNoGo creates a branch like `gonogo/fix-<scan_id_short>` before Claude Code starts applying fixes. The user reviews the diff and merges when satisfied.

**The user chooses at scan time** via a simple toggle:
- "Apply fixes to a new branch" (default)
- "Apply fixes directly to working directory"

For your personal use, you'll probably use direct edits. For other users, the branch default protects them.

---

## 3. The Rebuild/Redeploy Gap

**Decision: Branch-based deploy pipeline, user-configurable.**

The gap: after Claude Code applies fixes, someone needs to rebuild and redeploy so GoNoGo can rescan the *fixed* version. This should be automated but with the user in control.

### Recommended Setup

1. **GoNoGo creates a dedicated branch** (e.g., `gonogo/fix-<scan_id_short>`) at scan start.
2. **Claude Code applies fixes** to that branch.
3. **GoNoGo triggers a deploy command** that deploys *from that branch* to a preview/staging URL.
4. **GoNoGo rescans** the preview URL (not production).
5. **User merges to main** when satisfied → production deploy happens through their normal CI/CD.

### Deploy Command Configuration

The user configures a deploy command in GoNoGo settings (or per-scan):

```
# Examples:
vercel --branch gonogo/fix-abc123        # Vercel preview deploy
netlify deploy --alias gonogo-fix        # Netlify draft deploy  
railway up --branch gonogo/fix-abc123    # Railway preview
./deploy-preview.sh                      # Custom script
```

GoNoGo runs this command after fixes are applied, waits for the deploy URL, then rescans.

### Options Presented to User

| Option | When to Use |
|---|---|
| **Auto-deploy to preview branch** (default) | Best for most cases. Keeps production untouched. GoNoGo rescans the preview URL automatically. |
| **Manual rebuild + rescan** | User rebuilds/deploys themselves, then triggers rescan manually in GoNoGo UI. For complex deploy pipelines GoNoGo can't automate. |
| **Local dev server rescan** | For local development — GoNoGo rescans `localhost:3000` (or whatever). No deploy needed. Fastest loop. |

**Default: Auto-deploy to preview branch** — because GoNoGo is intended for not-yet-live apps, preview deploys are the natural fit. The branch-based approach keeps the automation clean: GoNoGo always reads from and deploys from its own branch, never touching main until the user explicitly merges.

**Key insight:** Since these are pre-production apps, there's no risk of deploying broken code to real users. The branch is a workspace, not a release.

---

## 4. Should the Loop Stop Early?

**Decision: Configurable cycle limit, sensible defaults.**

The user sets the max number of scan→fix→rescan cycles. Defaults:

| Setting | Default | Range |
|---|---|---|
| Max cycles | 3 | 1–10 |
| Stop on verdict | GO | GO / GO_WITH_CONDITIONS / never (manual stop only) |
| Stop on score threshold | none | 0–100 (optional) |

**How it works:**
- Cycle 1: Initial scan → fix critical/high → redeploy → rescan
- Cycle 2: Rescan finds remaining issues → fix → redeploy → rescan
- Cycle 3: Final check
- If verdict reaches "GO" (or user-configured target), loop stops regardless of remaining cycles.

**Diminishing returns are natural.** By cycle 2–3, the remaining findings are typically medium/low. The user can decide whether to keep going or ship.

---

## 5. Should Findings Severity Filter Escalate Per Cycle?

**Decision: No special escalation logic needed. The report handles this naturally.**

You're right — critical issues resolve in the first cycle. The report's priority ordering means:

- **Cycle 1:** Report is dominated by critical + high findings. User fixes those.
- **Cycle 2:** Rescan report now shows the critical/high tier as clean (or nearly). Medium findings are now the top priority. Any *new* issues introduced by fixes surface here too.
- **Cycle 3:** Polish pass — low findings, if the user cares to address them.

The severity filter the user selected in cycle 1 persists as the default for subsequent cycles, but they can adjust it. No need for GoNoGo to auto-escalate — the report's content naturally shifts downward in severity as fixes land.

**One useful addition:** In cycle 2+, the rescan report should include a "Delta" section at the top:
- "X findings resolved since last scan"
- "Y new findings introduced"  
- "Z findings unchanged"

This makes the progress tangible and immediately flags any regressions from Claude Code's fixes.

---

## 6. Where Do These Decisions Live?

**These decisions should be codified in two places:**

### A. `GONOGO_BUILD_SPEC.md` — New Section 14: Fix Loop Integration

Add a new section to the build spec covering:
- Report feed strategy (full vs. batched, user severity selection)
- Git branch strategy (default + direct edit option)
- Deploy pipeline configuration
- Cycle configuration (max cycles, stop conditions)
- Delta reporting for rescan cycles

### B. `GONOGO_PLANNING_DOC.md` — New Resolved Decision Items

Add to the "Resolved" list in Section 7:
- [x] **Report feed to Claude Code:** Full feed for <200k tokens (typical), batched by severity for larger reports. User selects which severity tiers to fix.
- [x] **Fix safety model:** Git branch by default (`gonogo/fix-<id>`), direct edits optional. User chooses at scan time.
- [x] **Rebuild/redeploy:** Branch-based preview deploy (default), manual rebuild, or local dev server rescan. Deploy command user-configurable.
- [x] **Loop cycle limits:** Configurable, default 3 cycles, stops on GO verdict.
- [x] **Severity escalation per cycle:** Not needed — report naturally deprioritizes as critical issues resolve. Delta section added for cycle 2+.

---

## Summary Table

| Question | Decision | Default |
|---|---|---|
| Full feed or batch? | Tiered, user selects severity tiers to fix | Full report, fix Critical + High |
| Claude Code breaks something? | Git branch isolates fixes | Branch (`gonogo/fix-<id>`) |
| User merge strategy? | User chooses: branch or direct edits | Branch |
| Rebuild/redeploy gap? | Auto-deploy preview from branch | Preview deploy via configured command |
| Loop stop early? | Configurable cycles + configurable verdict target | 3 cycles, stop on GO (configurable) |
| Severity filter escalate? | No — report handles naturally | N/A |
| Where do decisions live? | Build spec §14 + Planning doc §7 | — |
