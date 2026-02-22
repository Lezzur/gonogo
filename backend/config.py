import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Base paths
BASE_DIR = Path(__file__).resolve().parent
STORAGE_DIR = Path(os.getenv("STORAGE_DIR", BASE_DIR / "storage"))
SCREENSHOTS_DIR = STORAGE_DIR / "screenshots"
REPORTS_DIR = STORAGE_DIR / "reports"

# Database
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{(DATA_DIR / 'gonogo.db').as_posix()}")

# Server
BACKEND_PORT = int(os.getenv("BACKEND_PORT", 8000))
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")

# LLM
DEFAULT_LLM_PROVIDER = os.getenv("DEFAULT_LLM_PROVIDER", "gemini")
GEMINI_PRO_MODEL = os.getenv("GEMINI_PRO_MODEL", "gemini-3-pro-preview")
GEMINI_FLASH_MODEL = os.getenv("GEMINI_FLASH_MODEL", "gemini-3-flash-preview")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-5-20250929")

# Scan limits
MAX_DEEP_PAGES = int(os.getenv("MAX_DEEP_PAGES", 30))
MAX_SHALLOW_PAGES = int(os.getenv("MAX_SHALLOW_PAGES", 100))
MAX_SCAN_DURATION_SECONDS = int(os.getenv("MAX_SCAN_DURATION_SECONDS", 600))
MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", 10))

# Fix loop — cycle control
DEFAULT_MAX_CYCLES = int(os.getenv("DEFAULT_MAX_CYCLES", 3))
DEFAULT_STOP_ON_VERDICT = os.getenv("DEFAULT_STOP_ON_VERDICT", "GO")

# Fix loop — deployment & fix application
DEFAULT_DEPLOY_MODE = os.getenv("DEFAULT_DEPLOY_MODE", "branch")
DEFAULT_APPLY_MODE = os.getenv("DEFAULT_APPLY_MODE", "branch")
FIX_BRANCH_PREFIX = os.getenv("FIX_BRANCH_PREFIX", "gonogo/fix-")

# Fix loop — Claude Code integration
CLAUDE_CODE_PATH = os.getenv("CLAUDE_CODE_PATH", "claude")
CLAUDE_CODE_MAX_TURNS = int(os.getenv("CLAUDE_CODE_MAX_TURNS", 50))
CLAUDE_CODE_TIMEOUT_SECONDS = int(os.getenv("CLAUDE_CODE_TIMEOUT_SECONDS", 600))
CLAUDE_CODE_PERMISSION_MODE = os.getenv("CLAUDE_CODE_PERMISSION_MODE", "bypassPermissions")
CLAUDE_CODE_ALLOWED_TOOLS = os.getenv("CLAUDE_CODE_ALLOWED_TOOLS", "Read,Write,Edit,Bash(npm run *),Bash(npx *),Bash(git diff *),Bash(git status)")
CLAUDE_CODE_MAX_BUDGET_USD = float(os.getenv("CLAUDE_CODE_MAX_BUDGET_USD", 5.0))

# Ensure directories exist
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
