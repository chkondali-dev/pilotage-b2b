"""Print a generated tab module with proper UTF-8, optionally limited."""
import io
import sys

path = sys.argv[1]
limit = int(sys.argv[2]) if len(sys.argv) > 2 else 0
out = sys.stdout
try:
    out.reconfigure(encoding="utf-8")
except Exception:
    pass
lines = io.open(path, encoding="utf-8").read().splitlines()
for i, ln in enumerate(lines, 1):
    if limit and i > limit:
        print("... (%d lines total)" % len(lines))
        break
    print("%4d: %s" % (i, ln))
