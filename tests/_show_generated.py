"""Show + compile one generated tab module (helper for the migration)."""
import py_compile
import sys
from pathlib import Path

REPO = Path(r"C:/Users/hachk/pilotage_b2b")
MODES = [
    "tab0_executive.py",
    "tab1_tendances.py",
    "tab2_conventions.py",
    "tab3_magasins.py",
    "tab4_lens.py",
    "tab5_conventions.py",
    "tab6_crm.py",
    "tab7_alertes.py",
    "tab8_archive.py",
    "tab9_conformite.py",
]


def show(mode, n=40):
    p = REPO / "ui" / "tabs" / mode
    print(f"=== {mode} ===")
    for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
        if i > n:
            break
        print(f"{i:4}: {line}")
    try:
        py_compile.compile(p, doraise=True)
        print("PYCOMPILE_OK")
    except Exception as exc:
        print(f"PYCOMPILE_FAIL: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    show(sys.argv[1] if len(sys.argv) > 1 else "tab0_executive.py")
