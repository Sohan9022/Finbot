"""
Core Package Initialization
Loads .env and verifies important configuration.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# --------------------------------------------------------
# Load .env file from project root
# --------------------------------------------------------
BACKEND_DIR = Path(__file__).resolve().parent.parent
env_path = BACKEND_DIR / ".env"

load_dotenv(dotenv_path=env_path)

# --------------------------------------------------------
# VALIDATE TESSERACT PATH
# --------------------------------------------------------

# Read actual path from .env or config
TESSERACT_PATH = os.getenv("TESSERACT_PATH")

if TESSERACT_PATH and os.path.exists(TESSERACT_PATH):
    print(f"✔ Tesseract found at: {TESSERACT_PATH}")
else:
    print(f"⚠️ Tesseract not found at: {TESSERACT_PATH}")
    print("   OCR functionality may not work")

# --------------------------------------------------------
# PRINT ENVIRONMENT INFO
# --------------------------------------------------------

ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
print(f"✔ Environment: {ENVIRONMENT}")
print(f"✅ Core package initialized")
