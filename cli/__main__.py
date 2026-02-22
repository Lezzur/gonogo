"""GoNoGo TUI — Entry point.

Usage: python -m cli
"""

import sys
import os
from pathlib import Path

# Add backend/ to sys.path so we can import backend modules directly
backend_dir = str(Path(__file__).resolve().parent.parent / "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Windows event loop policy (required for Playwright)
if sys.platform == "win32":
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from cli.app import GoNoGoApp


def main():
    app = GoNoGoApp()
    app.run()


if __name__ == "__main__":
    main()
