"""Entry point for running the pipeline directly."""

from pathlib import Path
import sys

project_src = Path(__file__).resolve().parent / "src"
if str(project_src) not in sys.path:
    sys.path.insert(0, str(project_src))

from cli import main

if __name__ == "__main__":
    main()
