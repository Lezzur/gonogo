"""Git branch management for the GoNoGo fix loop."""

import asyncio
import logging
from pathlib import Path

from backend.config import FIX_BRANCH_PREFIX

logger = logging.getLogger(__name__)


class GitError(Exception):
    """Base exception for git operations."""

    pass


class NotAGitRepoError(GitError):
    """Raised when the path is not a git repository.

    Suggests using direct mode instead of branch mode.
    """

    def __init__(self, repo_path: str):
        message = (
            f"'{repo_path}' is not a git repository.\n\n"
            "Options:\n"
            "  1. Initialize git: cd <repo> && git init\n"
            "  2. Use apply_mode='direct' to apply fixes without git branching"
        )
        super().__init__(message)
        self.repo_path = repo_path


class DirtyWorkingTreeError(GitError):
    """Raised when the working tree has uncommitted changes."""

    def __init__(self, repo_path: str):
        message = (
            f"Working tree has uncommitted changes in '{repo_path}'.\n\n"
            "Commit or stash changes before starting the fix loop:\n"
            "  git add . && git commit -m 'WIP'\n"
            "  # or\n"
            "  git stash"
        )
        super().__init__(message)
        self.repo_path = repo_path


class BranchExistsError(GitError):
    """Raised when trying to create a branch that already exists."""

    def __init__(self, branch_name: str):
        message = f"Branch '{branch_name}' already exists"
        super().__init__(message)
        self.branch_name = branch_name


class GitManager:
    """Manages git branches for the fix loop.

    Stores the original branch name so we can switch back on cleanup.
    """

    def __init__(self):
        self._original_branches: dict[str, str] = {}

    async def _run_git(
        self, repo_path: str, *args: str, check: bool = True
    ) -> tuple[int, str, str]:
        """Run a git command and return (returncode, stdout, stderr)."""
        proc = await asyncio.create_subprocess_exec(
            "git",
            *args,
            cwd=repo_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        stdout_str = stdout.decode().strip()
        stderr_str = stderr.decode().strip()

        if check and proc.returncode != 0:
            raise GitError(f"git {' '.join(args)} failed: {stderr_str}")

        return proc.returncode, stdout_str, stderr_str

    async def is_git_repo(self, repo_path: str) -> bool:
        """Check if path is a git repository."""
        path = Path(repo_path)
        if not path.exists():
            return False

        returncode, _, _ = await self._run_git(
            repo_path, "rev-parse", "--git-dir", check=False
        )
        return returncode == 0

    async def get_current_branch(self, repo_path: str) -> str:
        """Return the current branch name."""
        if not await self.is_git_repo(repo_path):
            raise NotAGitRepoError(f"{repo_path} is not a git repository")

        _, stdout, _ = await self._run_git(repo_path, "rev-parse", "--abbrev-ref", "HEAD")
        return stdout

    def get_original_branch(self, repo_path: str) -> str:
        """Return the branch that was active before the fix branch was created."""
        repo_key = str(Path(repo_path).resolve())
        if repo_key not in self._original_branches:
            raise GitError(f"No original branch recorded for {repo_path}")
        return self._original_branches[repo_key]

    async def _has_uncommitted_changes(self, repo_path: str) -> bool:
        """Check if there are uncommitted changes."""
        returncode, _, _ = await self._run_git(
            repo_path, "diff", "--quiet", "HEAD", check=False
        )
        if returncode != 0:
            return True

        # Also check for untracked files that would be staged
        returncode, stdout, _ = await self._run_git(
            repo_path, "status", "--porcelain", check=False
        )
        return bool(stdout)

    async def _branch_exists(self, repo_path: str, branch: str) -> bool:
        """Check if a branch exists."""
        returncode, _, _ = await self._run_git(
            repo_path, "rev-parse", "--verify", f"refs/heads/{branch}", check=False
        )
        return returncode == 0

    async def create_fix_branch(
        self, repo_path: str, scan_id: str, auto_suffix: bool = True
    ) -> str:
        """Create and checkout a new fix branch.

        Args:
            repo_path: Path to the git repository.
            scan_id: The scan ID (first 8 chars used in branch name).
            auto_suffix: If True, automatically add suffix counter when branch exists.

        Returns:
            The created branch name.

        Raises:
            NotAGitRepoError: If repo_path is not a git repository.
            DirtyWorkingTreeError: If there are uncommitted changes.
            BranchExistsError: If the branch already exists and auto_suffix is False.
        """
        if not await self.is_git_repo(repo_path):
            logger.error(f"Not a git repository: {repo_path}")
            raise NotAGitRepoError(repo_path)

        # Check for uncommitted changes FIRST (before storing original branch)
        if await self._has_uncommitted_changes(repo_path):
            logger.error(f"Dirty working tree: {repo_path}")
            raise DirtyWorkingTreeError(repo_path)

        # Store original branch before switching
        original = await self.get_current_branch(repo_path)
        repo_key = str(Path(repo_path).resolve())
        self._original_branches[repo_key] = original
        logger.debug(f"Stored original branch '{original}' for {repo_path}")

        # Find available branch name (with suffix counter if needed)
        base_branch_name = f"{FIX_BRANCH_PREFIX}{scan_id[:8]}"
        branch_name = base_branch_name

        if await self._branch_exists(repo_path, branch_name):
            if not auto_suffix:
                raise BranchExistsError(branch_name)

            # Try suffixes: -2, -3, -4, ... up to -99
            for suffix in range(2, 100):
                candidate = f"{base_branch_name}-{suffix}"
                if not await self._branch_exists(repo_path, candidate):
                    branch_name = candidate
                    logger.info(f"Branch '{base_branch_name}' exists, using '{branch_name}' instead")
                    break
            else:
                # Exhausted all suffixes
                logger.error(f"Could not find available branch name for {base_branch_name}")
                raise BranchExistsError(f"All branch names {base_branch_name}-2 through {base_branch_name}-99 exist")

        # Create and checkout the branch
        try:
            await self._run_git(repo_path, "checkout", "-b", branch_name)
            logger.info(f"Created and checked out branch '{branch_name}'")
        except GitError as e:
            logger.error(f"Failed to create branch '{branch_name}': {e}")
            raise

        return branch_name

    async def get_diff_summary(self, repo_path: str, base_branch: str) -> dict:
        """Get a summary of changes compared to base branch.

        Returns:
            dict with keys: files_changed, insertions, deletions, files
        """
        if not await self.is_git_repo(repo_path):
            raise NotAGitRepoError(f"{repo_path} is not a git repository")

        # Get diff stats
        _, stdout, _ = await self._run_git(
            repo_path, "diff", "--stat", "--numstat", base_branch
        )

        files = []
        insertions = 0
        deletions = 0

        for line in stdout.split("\n"):
            if not line.strip():
                continue
            parts = line.split("\t")
            if len(parts) >= 3:
                # numstat format: insertions deletions filename
                try:
                    ins = int(parts[0]) if parts[0] != "-" else 0
                    dels = int(parts[1]) if parts[1] != "-" else 0
                    insertions += ins
                    deletions += dels
                    files.append(parts[2])
                except ValueError:
                    continue

        return {
            "files_changed": len(files),
            "insertions": insertions,
            "deletions": deletions,
            "files": files,
        }

    async def commit_fixes(self, repo_path: str, cycle_number: int) -> str:
        """Stage all changes and commit.

        Args:
            repo_path: Path to the git repository.
            cycle_number: The fix cycle number for the commit message.

        Returns:
            The commit hash.
        """
        if not await self.is_git_repo(repo_path):
            raise NotAGitRepoError(f"{repo_path} is not a git repository")

        # Stage all changes
        await self._run_git(repo_path, "add", "-A")

        # Commit
        message = f"GoNoGo fix cycle {cycle_number}"
        await self._run_git(repo_path, "commit", "-m", message)

        # Get commit hash
        _, stdout, _ = await self._run_git(repo_path, "rev-parse", "HEAD")
        return stdout

    async def switch_branch(self, repo_path: str, branch: str) -> None:
        """Checkout the specified branch."""
        if not await self.is_git_repo(repo_path):
            raise NotAGitRepoError(f"{repo_path} is not a git repository")

        await self._run_git(repo_path, "checkout", branch)

    async def delete_branch(self, repo_path: str, branch: str) -> None:
        """Delete the specified branch (for cleanup on discard)."""
        if not await self.is_git_repo(repo_path):
            raise NotAGitRepoError(f"{repo_path} is not a git repository")

        # Force delete to handle unmerged branches
        await self._run_git(repo_path, "branch", "-D", branch)
