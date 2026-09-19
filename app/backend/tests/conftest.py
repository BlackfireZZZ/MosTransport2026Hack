import sys
from pathlib import Path

# The backend is a flat module directory, run as `uvicorn main:app` from here.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
