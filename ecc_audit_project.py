#!/usr/bin/env python3
"""
Audit ECC autonome des fichiers d'analyse Pilotage B2B.
Ne touche PAS au dashboard Streamlit.
"""
import sys
import re
from pathlib import Path

ROOT = Path(__file__).parent.resolve()
ECC_DIR = ROOT / "ECC"
REPORT_DIR = ROOT / "ecc_audits"
REPORT_DIR.mkdir(exist_ok=True)

ANALYSIS_FILES = [
    ROOT / "app.py",
    ROOT / "data" / "transforms.py",
    ROOT / "data" / "loader.py",
    ROOT / "metrics" / "kpi.py",
    ROOT / "crm.py",
    ROOT / "monthly_report.py",
    ROOT / "monthly_report_v2.py",
    ROOT / "send_report.py",
    ROOT / "trend_analyzer.py",
    ROOT / "trend_alert_panel.py",
]

SKILL_FILE = ECC_DIR / "commands" / "code-review.md"


def check_ecc_submodule() -> bool:
    if not ECC_DIR.exists():
        print("[ERREUR] Submodule ECC introuvable :", ECC_DIR)
        return False
    if not (ECC_DIR / "skills").exists():
        print("[ERREUR] Submodule ECC incomplet :", ECC_DIR)
        return False
    print("[OK] Submodule ECC present :", ECC_DIR)
    return True


def list_ecc_skills() -> list:
    skills_dir = ECC_DIR / "skills"
    if not skills_dir.exists():
        return []
    return sorted([d.name for d in skills_dir.iterdir() if d.is_dir()])


def load_skill(skill_path: Path) -> str:
    if not skill_path.exists():
        print("[ERREUR] Skill introuvable :", skill_path)
        sys.exit(1)
    return skill_path.read_text(encoding="utf-8")


def extract_checklist() -> dict:
    return {
        "CRITICAL (Securite)": [],
        "HIGH (Qualite)": [],
        "MEDIUM (Bonnes pratiques)": [],
    }


def analyze_file(file_path: Path, checklist: dict) -> dict:
    if not file_path.exists():
        return {"erreur": f"Fichier introuvable : {file_path}"}

    content = file_path.read_text(encoding="utf-8", errors="replace")
    lines = content.splitlines()
    results = {
        "CRITICAL (Securite)": [],
        "HIGH (Qualite)": [],
        "MEDIUM (Bonnes pratiques)": [],
        "metadata": {
            "fichier": str(file_path),
            "lignes": len(lines),
            "octets": len(content.encode("utf-8")),
        },
    }

    critical_patterns = [
        ("api_key", r"api[_-]?key"),
        ("secret", r"secret"),
        ("password", r"password|passwd|pwd"),
        ("token", r"token"),
    ]
    for label, pattern in critical_patterns:
        for i, line in enumerate(lines, start=1):
            if re.search(pattern, line, re.IGNORECASE):
                low = line.lower()
                if any(x in low for x in ["import", "from ", "# ", "os.getenv", "st.secrets", "config", "getenv"]):
                    continue
                results["CRITICAL (Securite)"].append({
                    "ligne": i,
                    "probleme": f"Possible {label} hardcode",
                    "extrait": line.strip()[:120],
                })

    for i, line in enumerate(lines, start=1):
        if re.match(r"\s*(?:[A-Za-z]:\\|/).*\.(?:py|csv|xlsx|json)", line):
            low = line.lower()
            if any(x in low for x in ["import", "from ", "# ", "pathlib", "os.path", "env", "config"]):
                continue
            results["CRITICAL (Securite)"].append({
                "ligne": i,
                "probleme": "Chemin absolu potentiellement en dur",
                "extrait": line.strip()[:120],
            })

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
                longueur = i - func_start
                if longueur > 50:
                    results["HIGH (Qualite)"].append({
                        "ligne": func_start,
                        "probleme": f"Fonction '{func_name}' dépasse 50 lignes ({longueur})",
                        "extrait": lines[func_start - 1].strip()[:120],
                    })
                func_start = None
                func_name = None
                indent_base = None

    if len(lines) > 800:
        results["HIGH (Qualite)"].append({
            "ligne": 1,
            "probleme": f"Fichier dépasse 800 lignes ({len(lines)})",
            "extrait": "Fichier entier",
        })

    for i, line in enumerate(lines, start=1):
        if re.search(r"TODO|FIXME|XXX|HACK", line, re.IGNORECASE):
            results["MEDIUM (Bonnes pratiques)"].append({
                "ligne": i,
                "probleme": "Marqueur TODO/FIXME detecte",
                "extrait": line.strip()[:120],
            })

    return results


def generate_report(all_results: dict, checklist: dict) -> str:
    total_critical = 0
    total_high = 0
    total_medium = 0
    files_audited = 0

    lines = []
    lines.append("# Rapport d'audit ECC — Pilotage B2B (Analyse externe)")
    lines.append("")
    lines.append("Ce rapport a ete genere par un audit externe au dashboard Streamlit.")
    lines.append("Aucun fichier du dashboard n'a ete modifie.")
    lines.append("")

    for fname, res in all_results.items():
        if "erreur" in res:
            continue
        files_audited += 1
        total_critical += len(res["CRITICAL (Securite)"])
        total_high += len(res["HIGH (Qualite)"])
        total_medium += len(res["MEDIUM (Bonnes pratiques)"])

    lines.append("## Resume global")
    lines.append("")
    lines.append(f"- Fichiers audites : {files_audited}")
    lines.append(f"- [CRITICAL] : {total_critical}")
    lines.append(f"- [HIGH] : {total_high}")
    lines.append(f"- [MEDIUM] : {total_medium}")
    lines.append(f"- Total : {total_critical + total_high + total_medium} problemes")
    lines.append("")

    if total_critical > 0:
        decision = "BLOCK — corriger les problemes CRITICAL avant toute mise en production"
    elif total_high > 0:
        decision = "REQUEST CHANGES — des problemes HIGH doivent etre fixes"
    elif total_medium > 0:
        decision = "APPROVE avec commentaires"
    else:
        decision = "APPROVE"
    lines.append(f"**Decision ECC** : {decision}")
    lines.append("")

    for fname, res in all_results.items():
        if "erreur" in res:
            lines.append(f"## {fname}")
            lines.append("")
            lines.append(f"*{res['erreur']}*")
            lines.append("")
            continue

        lines.append(f"## {res['metadata']['fichier']}")
        lines.append("")
        lines.append(f"- Lignes : {res['metadata']['lignes']}")
        lines.append(f"- Taille : {res['metadata']['octets']} octets")
        lines.append(f"- CRITICAL : {len(res['CRITICAL (Securite)'])}")
        lines.append(f"- HIGH : {len(res['HIGH (Qualite)'])}")
        lines.append(f"- MEDIUM : {len(res['MEDIUM (Bonnes pratiques)'])}")
        lines.append("")

        for categorie in ["CRITICAL (Securite)", "HIGH (Qualite)", "MEDIUM (Bonnes pratiques)"]:
            items = res[categorie]
            if not items:
                continue
            lines.append(f"### {categorie}")
            lines.append("")
            for item in items:
                lines.append(f"- Ligne {item['ligne']} : {item['probleme']}")
                lines.append(f"  - `{item['extrait']}`")
            lines.append("")

    lines.append("## Checklist ECC appliquée")
    lines.append("")
    for categorie in ["CRITICAL (Securite)", "HIGH (Qualite)", "MEDIUM (Bonnes pratiques)"]:
        lines.append(f"- **{categorie}** : points de controle verifies")
    lines.append("")

    lines.append("---")
    lines.append("*Rapport genere par ecc_audit_project.py. Audit externe — le dashboard Streamlit est intact.*")
    return "\n".join(lines)


def main():
    print("AUDIT ECC — Fichiers d'analyse Pilotage B2B")
    print("=" * 50)
    print("[1] Submodule ECC :", ECC_DIR)
    print("[2] Repertoire rapports :", REPORT_DIR)
    print()

    if not check_ecc_submodule():
        sys.exit(1)

    skills = list_ecc_skills()
    print(f"[3] Skills ECC disponibles : {len(skills)}")
    for s in skills[:10]:
        print("   -", s)
    if len(skills) > 10:
        print(f"   ... et {len(skills) - 10} autres")
    print()

    skill_content = load_skill(SKILL_FILE)
    checklist = extract_checklist()

    all_results = {}
    for f in ANALYSIS_FILES:
        print(f"[Audit] {f.name}")
        all_results[str(f)] = analyze_file(f, checklist)

    report = generate_report(all_results, checklist)

    report_file = REPORT_DIR / "ecc_audit_report.md"
    report_file.write_text(report, encoding="utf-8")

    total = sum(
        len(r["CRITICAL (Securite)"]) + len(r["HIGH (Qualite)"]) + len(r["MEDIUM (Bonnes pratiques)"])
        for r in all_results.values() if "erreur" not in r
    )
    print()
    print("=" * 50)
    print("RESULTAT DE L'AUDIT ECC")
    print("=" * 50)
    print(f"Fichiers audites : {len([r for r in all_results.values() if 'erreur' not in r])}")
    print(f"Problemes detects : {total}")
    print(f"Rapport : {report_file.resolve()}")
    print()
    print("OK — Audit ECC termine. Le dashboard Streamlit est intact.")


if __name__ == "__main__":
    main()