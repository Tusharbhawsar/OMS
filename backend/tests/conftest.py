from pathlib import Path
import os
import sys


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("BATCH_SCHEDULER_ENABLED", "false")
