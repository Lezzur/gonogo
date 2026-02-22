"""Fix Loop Orchestrator — Automated scan→fix→redeploy→rescan cycle.

This module orchestrates the fully automated fix loop that:
1. Takes a completed scan with a Report A
2. Filters findings by severity
3. Invokes Claude Code to apply fixes
4. Deploys the fixed version
5. Rescans to verify fixes
6. Repeats until stop condition or max cycles
"""

import asyncio
import glob
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from backend.database import SessionLocal
from backend.models import FixCycle, Scan
from backend.schemas import FixLoopStartRequest
from backend.services.claude_code import (
    ClaudeCodeAuthError,
    ClaudeCodeNotInstalledError,
    ClaudeCodeRunner,
)
from backend.services.deploy_manager import DeployManager, DeployResult
from backend.services.git_manager import (
    DirtyWorkingTreeError,
    GitManager,
    NotAGitRepoError,
)
from backend.services.report_feed import generate_delta_report, prepare_feed
from backend.utils.progress import progress_manager

logger = logging.getLogger(__name__)


class FixLoopError(Exception):
    """Base exception for fix loop operations."""

    pass


class ScanNotFoundError(FixLoopError):
    """Raised when the scan is not found."""

    pass


class ScanNotCompletedError(FixLoopError):
    """Raised when the scan is not in completed status."""

    pass


class NoReportError(FixLoopError):
    """Raised when the scan has no report_a_path."""

    pass


class RescanFailedError(FixLoopError):
    """Raised when the rescan fails to complete."""

    def __init__(self, rescan_id: str, status: str, partial_results: Optional[dict] = None):
        message = f"Rescan {rescan_id} failed with status: {status}"
        super().__init__(message)
        self.rescan_id = rescan_id
        self.status = status
        self.partial_results = partial_results or {}


class FixLoopOrchestrator:
    """Orchestrates the fully automated fix loop.

    Once started, the loop runs to completion without human intervention,
    except when deploy_mode="manual" which requires the user to provide
    a deploy URL via the advance() method.
    """

    def __init__(
        self,
        scan_id: str,
        config: FixLoopStartRequest,
        db_session: Session,
        api_key: str,
        llm_provider: str = "gemini",
    ):
        """Initialize the fix loop orchestrator.

        Args:
            scan_id: The ID of the completed scan to start fixing.
            config: Configuration for the fix loop.
            db_session: SQLAlchemy database session.
            api_key: API key for LLM calls during rescans.
            llm_provider: LLM provider to use for rescans.
        """
        self.scan_id = scan_id
        self.config = config
        self.db = db_session
        self.api_key = api_key
        self.llm_provider = llm_provider

        # Initialize service managers
        self.git_manager = GitManager()
        self.deploy_manager = DeployManager()
        self.claude_code_runner = ClaudeCodeRunner()

        # State
        self.stop_requested = False
        self._deploy_url_event: Optional[asyncio.Event] = None
        self._manual_deploy_url: Optional[str] = None
        self._original_scan: Optional[Scan] = None
        self._fix_branch: Optional[str] = None

    def _load_scan(self) -> Scan:
        """Load and validate the original scan."""
        scan = self.db.query(Scan).filter(Scan.id == self.scan_id).first()
        if not scan:
            raise ScanNotFoundError(f"Scan {self.scan_id} not found")
        if scan.status != "completed":
            raise ScanNotCompletedError(
                f"Scan {self.scan_id} is not completed (status: {scan.status})"
            )
        if not scan.report_a_path:
            raise NoReportError(f"Scan {self.scan_id} has no Report A")
        return scan

    async def _broadcast(self, message: str, step: str = "fix_loop", percent: int = 0):
        """Broadcast a progress message via SSE."""
        await progress_manager.send_progress(self.scan_id, step, message, percent)

    def _get_severity_filter(self) -> list[str]:
        """Get the severity filter, defaulting to critical+high."""
        if self.config.severity_filter:
            return self.config.severity_filter
        return ["critical", "high"]

    def _get_tech_stack_string(self, scan: Scan) -> str:
        """Extract tech stack as a string for Claude Code context."""
        if not scan.tech_stack_detected:
            return ""
        ts = scan.tech_stack_detected
        parts = []
        if ts.get("framework"):
            parts.append(ts["framework"])
        if ts.get("ui_library"):
            parts.append(ts["ui_library"])
        if ts.get("language"):
            parts.append(ts["language"])
        if ts.get("notable_libraries"):
            parts.extend(ts["notable_libraries"][:3])
        return ", ".join(parts)

    def _extract_findings_from_scan(self, scan: Scan) -> list[dict]:
        """Extract findings list from a scan's synthesis data.

        The findings are stored in the scan's synthesis result which was
        used to generate the report. We need to reconstruct them from
        the lens_scores and findings_count, or re-read from the report.

        For simplicity, we'll use the findings_count as a proxy.
        A more complete implementation would parse the report or store
        the raw findings in the database.
        """
        # In a production implementation, we would store deduplicated_findings
        # in the database. For now, return empty list - delta will show
        # 0 resolved which is conservative but safe.
        return []

    async def run(self) -> None:
        """Run the fully automated fix loop.

        This method orchestrates the complete cycle:
        1. Create fix branch (if apply_mode="branch")
        2. For each cycle:
           a. Prepare filtered report
           b. Run Claude Code to apply fixes
           c. Commit changes (if branch mode)
           d. Deploy
           e. Wait for deployment
           f. Rescan
           g. Check stop conditions
        3. Broadcast completion summary
        """
        # Load and validate original scan
        self._original_scan = self._load_scan()
        scan = self._original_scan
        repo_path = self.config.repo_path

        # Update scan with fix loop config
        scan.fix_loop_enabled = True
        scan.max_cycles = self.config.max_cycles
        scan.stop_on_verdict = self.config.stop_on_verdict
        scan.deploy_mode = self.config.deploy_mode
        scan.deploy_command = self.config.deploy_command
        scan.severity_filter = self._get_severity_filter()
        scan.apply_mode = self.config.apply_mode
        scan.repo_path = repo_path
        self.db.commit()

        # Create fix branch if needed
        if self.config.apply_mode == "branch":
            await self._broadcast(
                f"Creating fix branch for scan {self.scan_id[:8]}...",
                "fix_loop_init",
                5,
            )
            try:
                self._fix_branch = await self.git_manager.create_fix_branch(
                    repo_path, self.scan_id
                )
                scan.fix_branch = self._fix_branch
                self.db.commit()
                logger.info(f"Created fix branch: {self._fix_branch}")
                await self._broadcast(
                    f"Created branch: {self._fix_branch}", "fix_loop_init", 10
                )
            except NotAGitRepoError as e:
                logger.error(f"Not a git repo: {e}")
                await progress_manager.send_error(self.scan_id, str(e))
                raise
            except DirtyWorkingTreeError as e:
                logger.error(f"Dirty working tree: {e}")
                await progress_manager.send_error(self.scan_id, str(e))
                raise
            except Exception as e:
                logger.error(f"Failed to create fix branch: {e}")
                await progress_manager.send_error(
                    self.scan_id, f"Failed to create fix branch: {e}"
                )
                raise

        # Initialize loop state
        current_report_path = scan.report_a_path
        previous_findings: list[dict] = []
        total_cost_usd = 0.0
        total_resolved = 0
        original_score = scan.overall_score or 0
        original_verdict = scan.verdict or "UNKNOWN"
        final_score = original_score
        final_verdict = original_verdict

        # Run fix cycles
        for cycle_number in range(1, self.config.max_cycles + 1):
            # Check stop request
            if self.stop_requested:
                await self._broadcast(
                    f"Fix loop stopped by user after cycle {cycle_number - 1}",
                    "fix_loop_stopped",
                    100,
                )
                break

            # Calculate progress percentage for this cycle
            cycle_base_percent = 10 + ((cycle_number - 1) / self.config.max_cycles) * 80

            # Create FixCycle record
            fix_cycle = FixCycle(
                id=str(uuid.uuid4()),
                scan_id=self.scan_id,
                cycle_number=cycle_number,
                status="fixing",
            )
            self.db.add(fix_cycle)
            scan.current_cycle = cycle_number
            self.db.commit()

            try:
                # Step a: Prepare filtered report
                await self._broadcast(
                    f"Cycle {cycle_number}/{self.config.max_cycles}: Preparing report for Claude Code...",
                    f"cycle_{cycle_number}_prepare",
                    int(cycle_base_percent),
                )
                filtered_report = prepare_feed(
                    current_report_path, self._get_severity_filter()
                )

                # Step b: Run Claude Code
                await self._broadcast(
                    f"Cycle {cycle_number}/{self.config.max_cycles}: Claude Code is fixing issues... (this may take several minutes)",
                    f"cycle_{cycle_number}_fixing",
                    int(cycle_base_percent + 5),
                )
                tech_stack = self._get_tech_stack_string(scan)

                try:
                    result = await self.claude_code_runner.run_fixes(
                        repo_path=repo_path,
                        report_content=filtered_report,
                        cycle_number=cycle_number,
                        tech_stack=tech_stack,
                    )
                except ClaudeCodeNotInstalledError as e:
                    logger.error(f"Claude Code not installed: {e}")
                    fix_cycle.status = "failed"
                    fix_cycle.error_message = str(e)
                    fix_cycle.completed_at = datetime.now(timezone.utc)
                    self.db.commit()
                    await progress_manager.send_error(self.scan_id, str(e))
                    raise
                except ClaudeCodeAuthError as e:
                    logger.error(f"Claude Code auth failure: {e}")
                    fix_cycle.status = "failed"
                    fix_cycle.error_message = str(e)
                    fix_cycle.completed_at = datetime.now(timezone.utc)
                    self.db.commit()
                    await progress_manager.send_error(self.scan_id, str(e))
                    raise

                # Update FixCycle with Claude Code results
                fix_cycle.claude_code_output = result.raw_output
                fix_cycle.claude_code_cost_usd = result.cost_usd
                fix_cycle.claude_code_duration_seconds = result.duration_seconds
                fix_cycle.files_modified = result.files_modified
                total_cost_usd += result.cost_usd
                self.db.commit()

                # Check for Claude Code failure
                if result.status == "budget_exceeded":
                    logger.warning(f"Claude Code budget exceeded in cycle {cycle_number}")
                    fix_cycle.status = "budget_exceeded"
                    fix_cycle.error_message = result.error_message
                    fix_cycle.completed_at = datetime.now(timezone.utc)
                    self.db.commit()
                    await self._broadcast(
                        f"Cycle {cycle_number}: Budget exceeded - partial fixes may have been applied. ${result.cost_usd:.2f} spent.",
                        f"cycle_{cycle_number}_budget_exceeded",
                        int(cycle_base_percent + 10),
                    )
                    # Continue to deploy/rescan to see what was fixed before budget ran out
                elif result.status != "success":
                    logger.error(f"Claude Code failed in cycle {cycle_number}: {result.error_message}")
                    fix_cycle.status = "failed"
                    fix_cycle.error_message = result.error_message or "Claude Code failed"
                    fix_cycle.completed_at = datetime.now(timezone.utc)
                    self.db.commit()
                    await self._broadcast(
                        f"Cycle {cycle_number}: Claude Code failed - {result.error_message}",
                        f"cycle_{cycle_number}_failed",
                        int(cycle_base_percent + 10),
                    )
                    break

                # Step c: Commit fixes (if branch mode)
                if self.config.apply_mode == "branch":
                    await self._broadcast(
                        f"Cycle {cycle_number}/{self.config.max_cycles}: Committing fixes...",
                        f"cycle_{cycle_number}_commit",
                        int(cycle_base_percent + 15),
                    )
                    try:
                        await self.git_manager.commit_fixes(repo_path, cycle_number)
                    except Exception as e:
                        # Non-fatal: may have no changes to commit
                        await self._broadcast(
                            f"Note: No changes to commit ({e})",
                            f"cycle_{cycle_number}_commit",
                            int(cycle_base_percent + 15),
                        )

                # Step d: Deploy
                await self._broadcast(
                    f"Cycle {cycle_number}/{self.config.max_cycles}: Deploying fixed version...",
                    f"cycle_{cycle_number}_deploy",
                    int(cycle_base_percent + 20),
                )
                fix_cycle.status = "deploying"
                self.db.commit()

                deploy_result = await self._handle_deploy(cycle_number, repo_path, scan.url)

                if deploy_result.status in ("deploy_failed", "failed"):
                    logger.error(f"Deploy failed in cycle {cycle_number}: {deploy_result.stderr}")
                    fix_cycle.status = "deploy_failed"
                    error_detail = deploy_result.stderr[:500] if deploy_result.stderr else "Unknown error"
                    fix_cycle.error_message = f"Deploy failed ({deploy_result.error_code or 'UNKNOWN'}): {error_detail}"
                    fix_cycle.completed_at = datetime.now(timezone.utc)
                    self.db.commit()
                    # Broadcast with full stderr for debugging
                    await progress_manager.send_error(
                        self.scan_id,
                        f"Deploy failed: {deploy_result.stderr}",
                    )
                    await self._broadcast(
                        f"Cycle {cycle_number}: Deploy failed - {error_detail}",
                        f"cycle_{cycle_number}_deploy_failed",
                        int(cycle_base_percent + 25),
                    )
                    break

                # Step e: Wait for deploy URL to be reachable
                rescan_url = deploy_result.deploy_url or scan.url
                await self._broadcast(
                    f"Cycle {cycle_number}/{self.config.max_cycles}: Waiting for deployment at {rescan_url}...",
                    f"cycle_{cycle_number}_wait_deploy",
                    int(cycle_base_percent + 30),
                )

                url_reachable = await self.deploy_manager.wait_for_url(rescan_url)
                if not url_reachable:
                    await self._broadcast(
                        f"Warning: Deploy URL not reachable after timeout, proceeding anyway",
                        f"cycle_{cycle_number}_wait_deploy",
                        int(cycle_base_percent + 35),
                    )

                # Step f: Rescan
                await self._broadcast(
                    f"Cycle {cycle_number}/{self.config.max_cycles}: Rescanning to verify fixes...",
                    f"cycle_{cycle_number}_rescan",
                    int(cycle_base_percent + 40),
                )
                fix_cycle.status = "rescanning"
                self.db.commit()

                try:
                    rescan_id = await self._run_rescan(rescan_url)
                    fix_cycle.rescan_id = rescan_id
                except Exception as e:
                    logger.error(f"Rescan failed in cycle {cycle_number}: {e}")
                    fix_cycle.status = "rescan_failed"
                    fix_cycle.error_message = f"Rescan failed: {e}"
                    fix_cycle.completed_at = datetime.now(timezone.utc)
                    self.db.commit()
                    await progress_manager.send_error(
                        self.scan_id, f"Rescan failed: {e}"
                    )
                    # Continue to next cycle or exit - the fixes were applied even if rescan failed
                    continue

                # Get rescan results
                rescan = self.db.query(Scan).filter(Scan.id == rescan_id).first()
                if rescan and rescan.status == "completed":
                    final_score = rescan.overall_score or 0
                    final_verdict = rescan.verdict or "UNKNOWN"
                    logger.info(f"Rescan completed: score={final_score}, verdict={final_verdict}")

                    # Calculate delta
                    current_findings = self._extract_findings_from_scan(rescan)
                    delta = generate_delta_report(current_findings, previous_findings)

                    fix_cycle.findings_resolved = delta["resolved_count"]
                    fix_cycle.findings_new = delta["new_count"]
                    fix_cycle.findings_unchanged = delta["unchanged_count"]
                    total_resolved += delta["resolved_count"]

                    # Update for next cycle
                    previous_findings = current_findings
                    current_report_path = rescan.report_a_path

                    # Broadcast delta
                    await self._broadcast(
                        f"Cycle {cycle_number}: {delta['resolved_count']} fixed, {delta['new_count']} new, "
                        f"{delta['unchanged_count']} unchanged. Score: {original_score}→{final_score}",
                        f"cycle_{cycle_number}_delta",
                        int(cycle_base_percent + 60),
                    )
                else:
                    # Rescan exists but didn't complete - store partial results
                    rescan_status = rescan.status if rescan else "not_found"
                    logger.warning(f"Rescan {rescan_id} did not complete: status={rescan_status}")
                    fix_cycle.status = "rescan_failed"
                    fix_cycle.error_message = f"Rescan status: {rescan_status}"

                    # Try to extract any partial results
                    if rescan:
                        partial_score = rescan.overall_score
                        if partial_score is not None:
                            logger.info(f"Storing partial rescan score: {partial_score}")
                            # Store partial findings info even if scan didn't complete
                            fix_cycle.findings_unchanged = rescan.findings_count or 0

                    fix_cycle.completed_at = datetime.now(timezone.utc)
                    self.db.commit()

                    await progress_manager.send_error(
                        self.scan_id,
                        f"Rescan did not complete (status: {rescan_status}). Partial results may be available.",
                    )
                    await self._broadcast(
                        f"Cycle {cycle_number}: Rescan failed (status: {rescan_status})",
                        f"cycle_{cycle_number}_rescan_failed",
                        int(cycle_base_percent + 60),
                    )

                # Mark cycle complete
                fix_cycle.status = "completed"
                fix_cycle.completed_at = datetime.now(timezone.utc)
                self.db.commit()

                # Step g: Check stop condition
                if self.config.stop_on_verdict != "never":
                    if final_verdict == self.config.stop_on_verdict:
                        await self._broadcast(
                            f"Target verdict '{self.config.stop_on_verdict}' reached after cycle {cycle_number}!",
                            "fix_loop_success",
                            95,
                        )
                        break
                    # Also check for GO when target is GO_WITH_CONDITIONS (GO is better)
                    if self.config.stop_on_verdict == "GO_WITH_CONDITIONS" and final_verdict == "GO":
                        await self._broadcast(
                            f"Exceeded target! Reached 'GO' after cycle {cycle_number}!",
                            "fix_loop_success",
                            95,
                        )
                        break

            except Exception as e:
                fix_cycle.status = "failed"
                fix_cycle.error_message = str(e)
                fix_cycle.completed_at = datetime.now(timezone.utc)
                self.db.commit()
                await progress_manager.send_error(
                    self.scan_id, f"Cycle {cycle_number} failed: {e}"
                )
                raise

        # Broadcast completion summary
        cycles_completed = scan.current_cycle or 0
        summary = (
            f"Fix loop complete: {cycles_completed} cycles, {total_resolved} issues resolved, "
            f"score {original_score}→{final_score} ({original_verdict}→{final_verdict}), "
            f"total cost ${total_cost_usd:.2f}"
        )
        logger.info(summary)
        await self._broadcast(summary, "fix_loop_complete", 100)

        if self.config.apply_mode == "branch" and self._fix_branch:
            await self._broadcast(
                f"Review and merge branch: {self._fix_branch}",
                "fix_loop_merge_reminder",
                100,
            )

        # Cleanup temp files
        self.cleanup_temp_files(repo_path)

    async def _handle_deploy(
        self, cycle_number: int, repo_path: str, original_url: str
    ) -> DeployResult:
        """Handle deployment based on deploy_mode."""
        deploy_mode = self.config.deploy_mode
        branch = self._fix_branch or "main"

        if deploy_mode == "local":
            # Local dev server mode - no deploy needed, use original URL
            return DeployResult(
                status="success",
                stdout="",
                stderr="",
                deploy_url=original_url,
                duration_seconds=0.0,
            )

        if deploy_mode == "manual":
            # Manual mode - wait for user to provide URL
            await self._broadcast(
                f"Cycle {cycle_number}: Awaiting deploy URL from user...",
                f"cycle_{cycle_number}_awaiting_deploy",
                0,
            )
            self._deploy_url_event = asyncio.Event()
            await self._deploy_url_event.wait()
            return DeployResult(
                status="success",
                stdout="",
                stderr="",
                deploy_url=self._manual_deploy_url,
                duration_seconds=0.0,
            )

        # Branch mode - run deploy command
        deploy_command = self.config.deploy_command
        if not deploy_command:
            # No deploy command configured, use original URL
            return DeployResult(
                status="success",
                stdout="No deploy command configured",
                stderr="",
                deploy_url=original_url,
                duration_seconds=0.0,
            )

        return await self.deploy_manager.trigger_deploy(
            deploy_command=deploy_command,
            branch=branch,
            cwd=repo_path,
            deploy_mode=deploy_mode,
            local_url=original_url,
        )

    async def _run_rescan(self, url: str) -> str:
        """Run a rescan and return the new scan ID."""
        from backend.scanner.orchestrator import run_scan

        # Create a new scan record for the rescan
        rescan = Scan(
            id=str(uuid.uuid4()),
            url=url,
            parent_scan_id=self.scan_id,
            status="pending",
        )
        self.db.add(rescan)
        self.db.commit()

        # Run the scan (this uses the same orchestrator as initial scans)
        await run_scan(
            scan_id=rescan.id,
            api_key=self.api_key,
            llm_provider=self.llm_provider,
        )

        return rescan.id

    async def advance(self, deploy_url: str) -> None:
        """Provide deploy URL for manual deploy mode.

        Args:
            deploy_url: The URL where the fixed version has been deployed.
        """
        if self._deploy_url_event is None:
            raise FixLoopError("Not waiting for deploy URL")
        self._manual_deploy_url = deploy_url
        self._deploy_url_event.set()

    async def request_stop(self) -> None:
        """Request the fix loop to stop after the current cycle.

        The current cycle will complete, then the loop will exit cleanly.
        """
        self.stop_requested = True
        await self._broadcast(
            "Stop requested - will stop after current cycle completes",
            "fix_loop_stopping",
            0,
        )

    def cleanup_temp_files(self, repo_path: str) -> int:
        """Remove all .gonogo-report-cycle-*.md temp files from the repo.

        Args:
            repo_path: Path to the repository.

        Returns:
            Number of files removed.
        """
        pattern = Path(repo_path) / ".gonogo-report-cycle-*.md"
        removed = 0
        for filepath in glob.glob(str(pattern)):
            try:
                Path(filepath).unlink()
                logger.debug(f"Removed temp file: {filepath}")
                removed += 1
            except Exception as e:
                logger.warning(f"Failed to remove temp file {filepath}: {e}")
        if removed:
            logger.info(f"Cleaned up {removed} temp report files from {repo_path}")
        return removed


async def start_fix_loop(
    scan_id: str,
    config: FixLoopStartRequest,
    api_key: str,
    llm_provider: str = "gemini",
) -> FixLoopOrchestrator:
    """Create and start a fix loop orchestrator.

    Args:
        scan_id: The ID of the completed scan to fix.
        config: Configuration for the fix loop.
        api_key: API key for LLM calls.
        llm_provider: LLM provider to use.

    Returns:
        The FixLoopOrchestrator instance (for control via advance/request_stop).
    """
    db = SessionLocal()
    orchestrator = FixLoopOrchestrator(
        scan_id=scan_id,
        config=config,
        db_session=db,
        api_key=api_key,
        llm_provider=llm_provider,
    )

    # Run in background task
    asyncio.create_task(orchestrator.run())

    return orchestrator
