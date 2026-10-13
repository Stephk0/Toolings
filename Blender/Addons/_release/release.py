"""Entry point: python Blender/Addons/_release/release.py <command> ... (see --help)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from st3e_release.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
