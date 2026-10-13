"""Dash N Dodge - run with: python main.py"""

import os

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

from dashndodge.app import main  # noqa: E402

if __name__ == "__main__":
    main()
