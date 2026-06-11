import sys
from pathlib import Path

# Renderer modules live flat in tiktok/ and import each other script-style.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
