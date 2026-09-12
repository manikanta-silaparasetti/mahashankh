import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
__package__ = "backend"

from .api import api_v1_router
print("Success importing api_v1_router:", api_v1_router)
