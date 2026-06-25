"""Main entry point for the SRE automation project."""

from __future__ import annotations

import warnings

warnings.filterwarnings(
    "ignore",
    message="Core Pydantic V1 functionality isn't compatible with Python 3.14 or greater.",
    category=UserWarning,
)


def main() -> None:
    """Run the SRE automation dashboard."""
    import subprocess
    subprocess.run(["streamlit", "run", "dashboard/app.py"])


if __name__ == "__main__":
    main()

# Made with Bob
