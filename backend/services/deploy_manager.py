"""Deploy manager for triggering and monitoring deployments."""

import asyncio
import logging
import re
import time
from typing import Optional

import httpx
from pydantic import BaseModel

from backend.config import DEFAULT_DEPLOY_MODE

logger = logging.getLogger(__name__)


class DeployResult(BaseModel):
    """Result of a deploy operation."""

    status: str  # "success", "failed", "timeout", "awaiting_url", "command_not_found"
    stdout: str
    stderr: str
    deploy_url: Optional[str] = None
    duration_seconds: float
    error_code: Optional[str] = None  # machine-readable error code for frontend


class DeployError(Exception):
    """Base exception for deploy operations."""

    pass


class CommandNotFoundError(DeployError):
    """Raised when the deploy command is not found."""

    pass


class DeployTimeoutError(DeployError):
    """Raised when the deploy command times out."""

    pass


class DeployManager:
    """Manages deployment triggering and URL polling."""

    # Common preview URL patterns
    URL_PATTERNS = [
        # Vercel
        r"https://[a-zA-Z0-9-]+\.vercel\.app",
        # Netlify
        r"https://[a-zA-Z0-9-]+\.netlify\.app",
        r"https://[a-zA-Z0-9-]+--[a-zA-Z0-9-]+\.netlify\.app",
        # Railway
        r"https://[a-zA-Z0-9-]+\.railway\.app",
        # Render
        r"https://[a-zA-Z0-9-]+\.onrender\.com",
        # Fly.io
        r"https://[a-zA-Z0-9-]+\.fly\.dev",
        # Cloudflare Pages
        r"https://[a-zA-Z0-9-]+\.pages\.dev",
        # AWS Amplify
        r"https://[a-zA-Z0-9-]+\.amplifyapp\.com",
        # Heroku
        r"https://[a-zA-Z0-9-]+\.herokuapp\.com",
        # Generic HTTPS URL on its own line
        r"https://[a-zA-Z0-9][a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(?:/[^\s]*)?",
    ]

    # Prefixes that often precede URLs in deploy output
    URL_PREFIXES = [
        r"Preview:\s*",
        r"URL:\s*",
        r"Deploy URL:\s*",
        r"Deployed to:\s*",
        r"Live at:\s*",
        r"Available at:\s*",
        r"Inspect:\s*",
        r"Website:\s*",
    ]

    async def trigger_deploy(
        self,
        deploy_command: str,
        branch: str,
        cwd: str,
        timeout_seconds: int = 300,
        deploy_mode: Optional[str] = None,
        local_url: Optional[str] = None,
    ) -> DeployResult:
        """Run the user-configured deploy command.

        Args:
            deploy_command: The command to run, with {branch} placeholder.
            branch: The branch name to substitute.
            cwd: Working directory for the command.
            timeout_seconds: Maximum time to wait for the command.
            deploy_mode: Override for DEFAULT_DEPLOY_MODE.
            local_url: URL to return for "local" deploy mode.

        Returns:
            DeployResult with status, output, and parsed URL if found.

        Raises:
            CommandNotFoundError: If the command executable is not found.
            DeployTimeoutError: If the command times out.
        """
        mode = deploy_mode or DEFAULT_DEPLOY_MODE
        start_time = time.time()

        # Handle special deploy modes
        if mode == "local":
            logger.info(f"Local deploy mode: using URL {local_url}")
            return DeployResult(
                status="success",
                stdout="",
                stderr="",
                deploy_url=local_url,
                duration_seconds=0.0,
            )

        if mode == "manual":
            logger.info("Manual deploy mode: awaiting user-provided URL")
            return DeployResult(
                status="awaiting_url",
                stdout="",
                stderr="",
                deploy_url=None,
                duration_seconds=0.0,
            )

        # Substitute {branch} placeholder
        command = deploy_command.replace("{branch}", branch)
        logger.info(f"Running deploy command: {command}")

        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                cwd=cwd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    proc.communicate(), timeout=timeout_seconds
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                duration = time.time() - start_time
                logger.error(f"Deploy command timed out after {timeout_seconds}s")
                # Return result instead of raising - allow orchestrator to handle
                return DeployResult(
                    status="deploy_failed",
                    stdout="",
                    stderr=f"Deploy command timed out after {timeout_seconds}s",
                    deploy_url=None,
                    duration_seconds=duration,
                    error_code="DEPLOY_TIMEOUT",
                )

            stdout = stdout_bytes.decode(errors="replace")
            stderr = stderr_bytes.decode(errors="replace")
            duration = time.time() - start_time

            logger.debug(f"Deploy stdout: {stdout[:500]}...")
            logger.debug(f"Deploy stderr: {stderr[:500]}...")

            if proc.returncode != 0:
                logger.error(f"Deploy command failed with exit code {proc.returncode}: {stderr}")
                return DeployResult(
                    status="deploy_failed",
                    stdout=stdout,
                    stderr=stderr,
                    deploy_url=None,
                    duration_seconds=duration,
                    error_code="DEPLOY_NONZERO_EXIT",
                )

            # Try to extract deploy URL from output
            deploy_url = self.detect_deploy_url(stdout) or self.detect_deploy_url(
                stderr
            )

            logger.info(f"Deploy succeeded in {duration:.1f}s, URL: {deploy_url}")
            return DeployResult(
                status="success",
                stdout=stdout,
                stderr=stderr,
                deploy_url=deploy_url,
                duration_seconds=duration,
            )

        except FileNotFoundError as e:
            duration = time.time() - start_time
            logger.error(f"Deploy command not found: {e}")
            return DeployResult(
                status="deploy_failed",
                stdout="",
                stderr=f"Command not found: {e}. Ensure the deploy tool is installed and in PATH.",
                deploy_url=None,
                duration_seconds=duration,
                error_code="DEPLOY_CMD_NOT_FOUND",
            )
        except OSError as e:
            duration = time.time() - start_time
            # Handle "command not found" errors on Windows
            if "The system cannot find the file specified" in str(e):
                logger.error(f"Deploy command not found (Windows): {e}")
                return DeployResult(
                    status="deploy_failed",
                    stdout="",
                    stderr=f"Command not found: {e}. Ensure the deploy tool is installed and in PATH.",
                    deploy_url=None,
                    duration_seconds=duration,
                    error_code="DEPLOY_CMD_NOT_FOUND",
                )
            logger.error(f"Deploy OS error: {e}")
            return DeployResult(
                status="deploy_failed",
                stdout="",
                stderr=str(e),
                deploy_url=None,
                duration_seconds=duration,
                error_code="DEPLOY_OS_ERROR",
            )

    async def wait_for_url(
        self, url: str, timeout_seconds: int = 120, poll_interval: int = 5
    ) -> bool:
        """Poll the URL until it responds with 2xx or times out.

        Args:
            url: The URL to poll.
            timeout_seconds: Maximum time to wait.
            poll_interval: Seconds between poll attempts.

        Returns:
            True if the URL became reachable, False if timed out.
        """
        start_time = time.time()
        deadline = start_time + timeout_seconds

        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            while time.time() < deadline:
                try:
                    response = await client.get(url)
                    if 200 <= response.status_code < 300:
                        return True
                except (httpx.RequestError, httpx.HTTPStatusError):
                    pass

                remaining = deadline - time.time()
                if remaining > 0:
                    await asyncio.sleep(min(poll_interval, remaining))

        return False

    def detect_deploy_url(self, stdout: str) -> Optional[str]:
        """Extract a deploy/preview URL from command output.

        Uses heuristics to find URLs from common deploy services.

        Args:
            stdout: The command output to parse.

        Returns:
            The detected URL, or None if not found.
        """
        if not stdout:
            return None

        lines = stdout.strip().split("\n")

        # First pass: look for URLs with known prefixes (highest confidence)
        for line in lines:
            line_stripped = line.strip()
            for prefix_pattern in self.URL_PREFIXES:
                match = re.search(
                    prefix_pattern + r"(https://[^\s]+)", line_stripped, re.IGNORECASE
                )
                if match:
                    url = match.group(1).rstrip(".,;:\"')")
                    return url

        # Second pass: look for known deploy service URLs
        for line in lines:
            line_stripped = line.strip()
            for pattern in self.URL_PATTERNS[:-1]:  # Exclude generic HTTPS pattern
                match = re.search(pattern, line_stripped)
                if match:
                    url = match.group(0).rstrip(".,;:\"')")
                    return url

        # Third pass: look for any HTTPS URL on its own line (or nearly alone)
        for line in lines:
            line_stripped = line.strip()
            # Line is mostly just a URL (allowing some prefix text)
            if len(line_stripped) < 200:
                match = re.search(r"https://[a-zA-Z0-9][^\s]+", line_stripped)
                if match:
                    url = match.group(0).rstrip(".,;:\"')")
                    # Validate it looks like a real URL
                    if re.match(r"https://[a-zA-Z0-9][a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", url):
                        return url

        return None
