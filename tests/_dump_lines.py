"""Dump a 1-based line range of app.py (helper for migration inspection)."""
import sys
from pathlib import Path

REPO = Path(r"C:/Users/hachk/pilotage_b2b")
APP = REPO / "app.py"


def main():
    start = int(sys.argv[1])
    end = int(sys.argv[2]) if len(sys.argv) > 2 else start
    lines = APP.read_text(encoding="utf-8").splitlines()
    out = sys.stdout
    try:
        out.reconfigure(encoding="utf-8")
    except Exception:
        pass
    for i in range(start - 1, min(end, len(lines))):
        print(f"{i + 1:4}: {lines[i]}")


if __name__ == "__main__":
    main()
