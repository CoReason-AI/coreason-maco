import sys
from pathlib import Path

# Add src to sys.path to allow imports like 'core.logger' and 'main'
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))
