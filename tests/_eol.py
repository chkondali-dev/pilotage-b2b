"""Report line endings (CRLF vs LF) for a few files."""
import io
import sys

paths = sys.argv[1:]
for p in paths:
    b = io.open(p, "rb").read()
    crlf = b.count(b"\r\n")
    lf_only = b.count(b"\n") - crlf
    print("%-40s CRLF=%d LF=%d %s" % (p, crlf, lf_only, "CRLF" if crlf and not lf_only else ("LF" if lf_only and not crlf else "MIXED")))
