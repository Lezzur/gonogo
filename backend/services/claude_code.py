"""Claude Code integration service for automated fix application."""

import asyncio
import json
import re
from pathlib import Path
from typing import Optional

from pydantic import BaseModel

from backend.config import (
    CLAUDE_CODE_ALLOWED_TOOLS,
    CLAUDE_CODE_MAX_BUDGET_USD,
    CLAUDE_CODE_MAX_TURNS,
    CLAUDE_CODE_PATH,
    CLAUDE_CODE_PERMISSION_MODE,
    CLAUDE_CODE_TIMEOUT_SECONDS,
)


class ClaudeCodeResult(BaseModel):
    """Result from a Claude Code fix session."""

    status: str  # "success", "error", "timeout"
    result_text: str
    cost_usd: float
    duration_seconds: float
    session_id: Optional[str] = None
    files_modified: list[str]
    error_message: Optional[str] = None
    raw_output: str


class ClaudeCodeError(Exception):
    """Base exception for Claude Code operations."""

    pass


class ClaudeCodeNotInstalledError(ClaudeCodeError):
    """Raised when Claude Code binary is not found or not executable."""

    pass


class ClaudeCodeAuthError(ClaudeCodeError):
    """Raised when Claude Code is not authenticated."""

    pass


class ClaudeCodeRunner:
    """Runs Claude Code in headless mode to apply fixes from GoNoGo reports.

    Invokes Claude Code as a subprocess with the filtered Report A written to
    a temp file in the repo directory. Claude Code reads the report and fixes
    all findings autonomously.
    """

    def __init__(
        self,
        claude_code_path: str = CLAUDE_CODE_PATH,
        max_turns: int = CLAUDE_CODE_MAX_TURNS,
        timeout: int = CLAUDE_CODE_TIMEOUT_SECONDS,
        permission_mode: str = CLAUDE_CODE_PERMISSION_MODE,
        allowed_tools: str = CLAUDE_CODE_ALLOWED_TOOLS,
        max_budget_usd: float = CLAUDE_CODE_MAX_BUDGET_USD,
    ):
        self.claude_code_path = claude_code_path
        self.max_turns = max_turns
        self.timeout = timeout
        self.permission_mode = permission_mode
        self.allowed_tools = allowed_tools
        self.max_budget_usd = max_budget_usd

    async def check_installed(self) -> tuple[bool, str]:
        """Check if Claude Code is installed and return version.

        Returns:
            Tuple of (is_installed, version_or_error_message)
        """
        try:
            proc = await asyncio.create_subprocess_exec(
                self.claude_code_path,
                "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=10)

            if proc.returncode == 0:
                version = stdout.decode().strip()
                return True, version
            else:
                error = stderr.decode().strip() or stdout.decode().strip()
                return False, f"Claude Code returned error: {error}"

        except FileNotFoundError:
            return False, f"Claude Code binary not found at '{self.claude_code_path}'"
        except asyncio.TimeoutError:
            return False, "Timeout while checking Claude Code version"
        except Exception as e:
            return False, f"Error checking Claude Code: {e}"

    async def run_fixes(
        self,
        repo_path: str,
        report_content: str,
        cycle_number: int,
        tech_stack: str = "",
    ) -> ClaudeCodeResult:
        """Run Claude Code to fix all findings in the report.

        Args:
            repo_path: Path to the target repository.
            report_content: The filtered GoNoGo report content (markdown).
            cycle_number: The fix cycle number (1, 2, 3...).
            tech_stack: Optional tech stack description for context.

        Returns:
            ClaudeCodeResult with status, modified files, cost, etc.

        Raises:
            ClaudeCodeNotInstalledError: If Claude Code binary is not available.
            ClaudeCodeAuthError: If Claude Code is not authenticated.
        """
        # Verify Claude Code is installed
        is_installed, version_or_error = await self.check_installed()
        if not is_installed:
            raise ClaudeCodeNotInstalledError(version_or_error)

        # Write report to temp file in repo (avoids stdin issues with large content)
        report_filename = f".gonogo-report-cycle-{cycle_number}.md"
        report_path = Path(repo_path) / report_filename

        try:
            report_path.write_text(report_content, encoding="utf-8")
        except Exception as e:
            return ClaudeCodeResult(
                status="error",
                result_text="",
                cost_usd=0.0,
                duration_seconds=0.0,
                files_modified=[],
                error_message=f"Failed to write report file: {e}",
                raw_output="",
            )

        # Build the prompt
        prompt = (
            f"Read the GoNoGo QA report at {report_filename} in this project directory. "
            "It contains findings from an automated quality audit of this codebase, organized by severity. "
            "Fix every finding listed, starting with Critical, then High, then Medium, then Low. "
            "For each finding: read the relevant source files, understand the issue described, "
            "and implement the fix as specified in the 'Fix' instruction. "
            "After all fixes are applied, list every file you modified."
        )
        if tech_stack:
            prompt += f" This project uses: {tech_stack}"

        # Build command args
        cmd = [
            self.claude_code_path,
            "-p",
            "--cwd",
            str(repo_path),
            "--permission-mode",
            self.permission_mode,
            "--output-format",
            "json",
            "--max-turns",
            str(self.max_turns),
            "--max-budget-usd",
            str(self.max_budget_usd),
        ]

        # --allowedTools is only relevant when permission_mode is "acceptEdits"
        if self.permission_mode == "acceptEdits":
            cmd.extend(["--allowedTools", self.allowed_tools])

        # Add the prompt as the final positional arg
        cmd.append(prompt)

        # Run Claude Code
        start_time = asyncio.get_event_loop().time()
        proc = None

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=self.timeout
                )
            except asyncio.TimeoutError:
                # Kill the process tree on timeout
                await self._kill_process_tree(proc)
                duration = asyncio.get_event_loop().time() - start_time
                return ClaudeCodeResult(
                    status="timeout",
                    result_text="",
                    cost_usd=0.0,
                    duration_seconds=duration,
                    files_modified=[],
                    error_message=f"Claude Code timed out after {self.timeout} seconds",
                    raw_output="",
                )

            duration = asyncio.get_event_loop().time() - start_time
            stdout_str = stdout.decode("utf-8", errors="replace")
            stderr_str = stderr.decode("utf-8", errors="replace")

            # Check for auth failure
            combined_output = stdout_str + stderr_str
            if "not authenticated" in combined_output.lower():
                raise ClaudeCodeAuthError(
                    "Claude Code is not authenticated. Run 'claude login' to authenticate."
                )

            # Non-zero exit code
            if proc.returncode != 0:
                return ClaudeCodeResult(
                    status="error",
                    result_text="",
                    cost_usd=0.0,
                    duration_seconds=duration,
                    files_modified=[],
                    error_message=f"Claude Code exited with code {proc.returncode}: {stderr_str}",
                    raw_output=stdout_str,
                )

            # Parse JSON output
            return self._parse_output(stdout_str, duration)

        finally:
            # Clean up the report file
            self._cleanup_report_file(report_path)

    def _parse_output(self, stdout: str, duration: float) -> ClaudeCodeResult:
        """Parse Claude Code's JSON output."""
        try:
            data = json.loads(stdout)
        except json.JSONDecodeError as e:
            return ClaudeCodeResult(
                status="error",
                result_text="",
                cost_usd=0.0,
                duration_seconds=duration,
                files_modified=[],
                error_message=f"Failed to parse JSON output: {e}",
                raw_output=stdout,
            )

        # Extract fields from Claude Code output
        # Expected: {"type": "result", "subtype": "success"|"error", "result": "...", "total_cost_usd": 0.xx, ...}
        result_type = data.get("type", "")
        subtype = data.get("subtype", "")
        result_text = data.get("result", "")
        cost_usd = data.get("total_cost_usd", 0.0)
        duration_ms = data.get("duration_ms", duration * 1000)
        session_id = data.get("session_id")
        is_error = data.get("is_error", False)

        # Determine status
        if is_error or subtype == "error":
            status = "error"
            error_message = result_text
        else:
            status = "success"
            error_message = None

        # Extract modified files from result text
        files_modified = self._extract_modified_files(result_text)

        return ClaudeCodeResult(
            status=status,
            result_text=result_text,
            cost_usd=cost_usd,
            duration_seconds=duration_ms / 1000,
            session_id=session_id,
            files_modified=files_modified,
            error_message=error_message,
            raw_output=stdout,
        )

    def _extract_modified_files(self, result_text: str) -> list[str]:
        """Extract list of modified files from Claude Code's result text.

        Claude Code is prompted to list modified files at the end.
        Look for common patterns like:
        - "Modified files:" followed by a list
        - File paths in the text (e.g., src/foo.ts, ./bar.js)
        """
        files = set()

        # Pattern 1: Look for a "Modified files:" or "Files modified:" section
        modified_section_match = re.search(
            r"(?:modified|changed|edited|updated)\s*files?:?\s*\n((?:[-*•]\s*[^\n]+\n?)+)",
            result_text,
            re.IGNORECASE,
        )
        if modified_section_match:
            section = modified_section_match.group(1)
            for line in section.split("\n"):
                # Extract file path from bullet points
                file_match = re.search(r"[-*•]\s*`?([^`\n]+)`?", line)
                if file_match:
                    filepath = file_match.group(1).strip()
                    if self._looks_like_filepath(filepath):
                        files.add(filepath)

        # Pattern 2: Look for inline file paths that look like code files
        # Match paths like: src/foo.ts, ./bar.js, components/Button.tsx
        path_pattern = r"(?:^|[\s`\"\'])(\.?/?(?:[\w.-]+/)*[\w.-]+\.(?:ts|tsx|js|jsx|css|scss|html|vue|svelte|json|md|py|rb|go|rs|java|kt|swift|c|cpp|h|hpp))"
        for match in re.finditer(path_pattern, result_text, re.MULTILINE):
            filepath = match.group(1).strip()
            if self._looks_like_filepath(filepath):
                files.add(filepath)

        return sorted(files)

    def _looks_like_filepath(self, s: str) -> bool:
        """Heuristic check if a string looks like a file path."""
        if not s or len(s) < 3 or len(s) > 200:
            return False
        # Must have an extension
        if "." not in s:
            return False
        # Should not have spaces (unless escaped)
        if " " in s and "\\ " not in s:
            return False
        # Should not be a URL
        if s.startswith(("http://", "https://", "ftp://")):
            return False
        return True

    async def _kill_process_tree(self, proc: asyncio.subprocess.Process) -> None:
        """Kill a process and its children."""
        try:
            proc.terminate()
            try:
                await asyncio.wait_for(proc.wait(), timeout=5)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
        except ProcessLookupError:
            pass  # Process already terminated

    def _cleanup_report_file(self, report_path: Path) -> None:
        """Remove the temporary report file."""
        try:
            if report_path.exists():
                report_path.unlink()
        except Exception:
            pass  # Best effort cleanup
