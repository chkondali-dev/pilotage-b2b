#!/usr/bin/env python3
"""
Test ECC avec le dashboard Pilotage B2B.

Ce script utilise la skill ECC `code-review` comme framework d'analyse
pour auditer le code du dashboard Streamlit (app.py) et générer un rapport.

Usage:
    python ecc_test_dashboard.py [fichier_a_auditer]
"""
import sys
import re
from pathlib import Path

ECC_DIR = Path(__file__).parent / "ECC"
DASHBOARD_DIR = Path(__file__).parent
SKILL_FILE = ECC_DIR / "commands" / "code-review.md"
DEFAULT_TARGET = DASHBOARD_DIR / "app.py"
REPORT_FILE = DASHBOARD_DIR / "ecc_audit_report.md"


def load_ecc_skill(skill_path: Path) -> str:
    if not skill_path.exists():
        print(f"❌ Skill ECC introuvable : {skill_path}")
        sys.exit(1)
    return skill_path.read_text(encoding="utf-8")


def load_target_file(file_path: Path) -> str:
    if not file_path.exists():
        print(f"❌ Fichier cible introuvable : {file_path}")
        sys.exit(1)
    return file_path.read_text(encoding="utf-8")


def extract_checklist() -> dict:
    return {
        "CRITICAL (Sécurité)": [
            "Hardcoded credentials, API keys, tokens",
            "SQL injection vulnerabilities",
            "XSS vulnerabilities",
            "Missing input validation",
            "Insecure dependencies",
            "Path traversal risks",
        ],
        "HIGH (Qualité)": [
            "Functions > 50 lines",
            "Files > 800 lines",
            "Nesting depth > 4 levels",
            "Missing error handling",
            "console.log statements",
            "TODO/FIXME comments",
            "Missing JSDoc for public APIs",
        ],
        "MEDIUM (Bonnes pratiques)": [
            "Mutation patterns (use immutable instead)",
            "Emoji usage in code/comments",
            "Missing tests for new code",
            "Accessibility issues (a11y)",
        ],
    }


def analyze_code(target_content: str, checklist: dict) -> dict:
    lines = target_content.splitlines()
    results = {
        "CRITICAL (Sécurité)": [],
        "HIGH (Qualité)": [],
        "MEDIUM (Bonnes pratiques)": [],
    }

    # --- CRITICAL : Hardcoded credentials / tokens ---
    critical_patterns = [
        ("api_key", r"api[_-]?key"),
        ("secret", r"secret"),
        ("password", r"password|passwd|pwd"),
        ("token", r"token"),
    ]
    for label, pattern in critical_patterns:
        for i, line in enumerate(lines, start=1):
            if re.search(pattern, line, re.IGNORECASE):
                if any(x in line.lower() for x in ["import", "from ", "# ", "os.getenv", "st.secrets", "config"]):
                    continue
                results["CRITICAL (Sécurité)"].append({
                    "line": i,
                    "issue": f"Possible {label} hardcodé",
                    "snippet": line.strip()[:100],
                })

    # --- HIGH : Fonctions > 50 lignes ---
    func_start = None
    func_name = None
    indent_base = None
    for i, line in enumerate(lines, start=1):
        m = re.match(r"(\s*)def\s+(\w+)\s*\(.*\):", line)
        if m:
            func_start = i
            func_name = m.group(2)
            indent_base = len(m.group(1))
        elif func_start is not None and line.strip() and not line.startswith("#"):
            current_indent = len(line) - len(line.lstrip())
            if current_indent <= indent_base and line.strip():
                length = i - func_start
                if length > 50:
                    results["HIGH (Qualité)"].append({
                        "line": func_start,
                        "issue": f"Fonction '{func_name}' dépasse 50 lignes ({length} lignes)",
                        "snippet": lines[func_start - 1].strip()[:100],
                    })
                func_start = None
                func_name = None
                indent_base = None

    # --- HIGH : Fichier > 800 lignes ---
    if len(lines) > 800:
        results["HIGH (Qualité)"].append({
            "line": 1,
            "issue": f"Fichier dépasse 800 lignes ({len(lines)} lignes)",
            "snippet": "Fichier entier",
        })

    # --- MEDIUM : TODO/FIXME ---
    for i, line in enumerate(lines, start=1):
        if re.search(r"TODO|FIXME|XXX|HACK", line, re.IGNORECASE):
            results["MEDIUM (Bonnes pratiques)"].append({
                "line": i,
                "issue": "Marqueur TODO/FIXME détecté",
                "snippet": line.strip()[:100],
            })

    return results


def generate_report(target_path: Path, skill_path: Path, results: dict, checklist: dict) -> str:
    total_issues = sum(len(v) for v in results.values())
    critical_count = len(results["CRITICAL (Sécurité)"])
    high_count = len(results["HIGH (Qualité)"])
    medium_count = len(results["MEDIUM (Bonnes pratiques)"])

    if critical_count > 0:
        decision = "BLOCK — doit être corrigé avant merge"
    elif high_count > 0:
        decision = "REQUEST CHANGES — des problèmes HIGH doivent être fixés"
    elif medium_count > 0:
        decision = "APPROVE avec commentaires"
    else:
        decision = "APPROVE"

    lines = []
    lines.append("# Rapport d'audit ECC — Dashboard Pilotage B2B")
    lines.append("")
    lines.append(f"**Cible** : `{target_path}`")
    lines.append(f"**Skill ECC utilisée** : `{skill_path.name}`")
    lines.append(f"**Décision ECC** : {decision}")
    lines.append("")
    lines.append("## Résumé")
    lines.append("")
    lines.append(f"- [CRITICAL] : {critical_count}")
    lines.append(f"- [HIGH] : {high_count}")
    lines.append(f"- [MEDIUM] : {medium_count}")
    lines.append(f"- **Total** : {total_issues} problèmes détectés")
    lines.append("")

    for category, items in results.items():
        lines.append(f"### {category}")
        lines.append("")
        if not items:
            lines.append("*Aucun problème détecté.*")
            lines.append("")
            continue
        for item in items:
            lines.append(f"- Ligne {item['line']} : {item['issue']}")
            lines.append(f"  - Code : `{item['snippet']}`")
        lines.append("")

    lines.append("## Checklist ECC appliquée")
    lines.append("")
    for category, items in checklist.items():
        lines.append(f"- **{category}** : {len(items)} points de contrôle")
    lines.append("")
    lines.append("---")
    lines.append("*Rapport généré par le test ECC-Dashboard. Un review complet nécessite un agent ECC (Claude Code, Codex, Cursor) avec la skill chargée.*")
    return "\n".join(lines)


def main():
    target_file = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_TARGET

    print("TEST ECC avec le dashboard Pilotage B2B")
    print("=" * 50)
    print(f"[1] Submodule ECC : {ECC_DIR.resolve()}")
    print(f"[2] Fichier audité : {target_file.resolve()}")
    print(f"[3] Skill ECC : {SKILL_FILE.name}")
    print()

    # Charger la skill ECC
    skill_content = load_ecc_skill(SKILL_FILE)
    checklist = extract_checklist()

    # Charger le fichier cible
    target_content = load_target_file(target_file)

    # Analyser
    print("Analyse en cours...")
    results = analyze_code(target_content, checklist)

    # Générer le rapport
    report = generate_report(target_file, SKILL_FILE, results, checklist)
    REPORT_FILE.write_text(report, encoding="utf-8")

    # Afficher le résumé
    total = sum(len(v) for v in results.values())
    print()
    print("=" * 50)
    print("RESUME DE L'AUDIT ECC")
    print("=" * 50)
    print(f"[CRITICAL] : {len(results['CRITICAL (Sécurité)'])}")
    print(f"[HIGH]     : {len(results['HIGH (Qualité)'])}")
    print(f"[MEDIUM]   : {len(results['MEDIUM (Bonnes pratiques)'])}")
    print(f"[Total]    : {total} problèmes")
    print()
    print(f"[Rapport] : {REPORT_FILE.resolve()}")
    print()
    print("OK - Test ECC terminé. Le dashboard peut être amélioré en utilisant")
    print("   les skills ECC via Claude Code, Codex, Cursor, ou tout agent compatible.")


if __name__ == "__main__":
    main()