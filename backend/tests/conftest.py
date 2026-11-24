import os
import sys
import tempfile
from pathlib import Path

# Fixed clinic clock and a throwaway database BEFORE the app is imported.
os.environ["CLINIC_NOW"] = "2026-11-02 10:00"
os.environ["DATABASE_URL"] = f"sqlite:///{Path(tempfile.mkdtemp()) / 'test.db'}"
os.environ["AI_ENABLED"] = "false"
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
