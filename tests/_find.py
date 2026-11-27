"""Find lines in app.py matching a literal substring (case-sensitive)."""
import io
import sys

APP = r"C:/Users/hachk/pilotage_b2b/app.py"
pat = sys.argv[1]
out = sys.stdout
try:
    out.reconfigure(encoding="utf-8")
except Exception:
    pass
for i, line in enumerate(io.open(APP, encoding="utf-8").read().splitlines(), 1):
    if pat in line:
        print(f"{i:5}: {line}")
