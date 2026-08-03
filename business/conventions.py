"""
conventions.py — Registre unique de suivi des conventions (Business Core).

Remplace les copies data/conventions_signees.csv du dashboard et du contract lab :
un seul fichier, un seul point d'écriture. Les écrans et les workflows passent par ici.

Ponytail: CSV mono-fichier sans verrou — à passer en SQLite si des écritures
concurrentes apparaissent.
"""
import csv as _csv
import re
from datetime import date
from pathlib import Path

REGISTRY_PATH = Path(__file__).resolve().parent.parent / "data" / "conventions_signees.csv"
FIELDS = ["code", "client", "scenario", "garantie", "statut",
          "date_debut_prospection", "date_signature", "nb_modifications", "notes"]


def _read() -> list[dict]:
    if not REGISTRY_PATH.exists():
        return []
    with open(REGISTRY_PATH, encoding="utf-8") as f:
        return list(_csv.DictReader(f, delimiter=";"))


def _write(rows: list[dict]) -> None:
    REGISTRY_PATH.parent.mkdir(exist_ok=True)
    with open(REGISTRY_PATH, "w", newline="", encoding="utf-8") as f:
        w = _csv.DictWriter(f, fieldnames=FIELDS, delimiter=";")
        w.writeheader()
        w.writerows(rows)


def load_all() -> list[dict]:
    """Toutes les lignes du registre (lecture seule)."""
    return _read()


def load_convention(code: str) -> dict | None:
    """Ligne du registre par code (insensible à la casse). None si absente."""
    code = code.strip().lower()
    return next((r for r in _read()
                 if str(r.get("code", "")).strip().lower() == code), None)


def register_convention(code: str, client: str, scenario: str = "", garantie: str = "",
                        statut: str = "Prospection", date_debut_prospection: str | None = None,
                        date_signature: str = "", notes: str = "") -> str:
    """Upsert : crée ou met à jour une ligne. Retourne "created" | "updated".

    En mise à jour, seuls les champs fournis sont remplacés (pas de reset du statut).
    nb_modifications est incrémenté à chaque mise à jour.
    """
    code = re.sub(r"[^A-Z0-9_]", "_", code.strip().upper())[:20]
    rows = _read()
    for r in rows:
        if str(r.get("code", "")).strip().lower() == code.lower():
            updates = {"client": client, "scenario": scenario, "garantie": garantie,
                       "statut": statut, "date_signature": date_signature, "notes": notes}
            if date_debut_prospection is not None:
                updates["date_debut_prospection"] = date_debut_prospection
            for k, v in updates.items():
                if v:
                    r[k] = v
            r["nb_modifications"] = str(int(r.get("nb_modifications") or 0) + 1)
            _write(rows)
            return "updated"
    rows.append({"code": code, "client": client, "scenario": scenario, "garantie": garantie,
                 "statut": statut,
                 "date_debut_prospection": date_debut_prospection or date.today().isoformat(),
                 "date_signature": date_signature, "nb_modifications": "0", "notes": notes})
    _write(rows)
    return "created"


def update_convention(code: str, **fields) -> dict | None:
    """Met à jour statut/notes/… ; retourne la ligne mise à jour, None si rien n'a changé.

    nb_modifications est incrémenté quand statut ou notes changent réellement
    (règle héritée du dashboard — un archivage compte comme une modification).
    """
    target = code.strip().lower()
    rows = _read()
    for r in rows:
        if str(r.get("code", "")).strip().lower() == target:
            changed = False
            for k, v in fields.items():
                if k in FIELDS and v is not None and str(r.get(k, "")) != str(v):
                    r[k] = str(v)
                    changed = True
            if changed:
                r["nb_modifications"] = str(int(r.get("nb_modifications") or 0) + 1)
                _write(rows)
                return r
            return None
    return None


if __name__ == "__main__":
    # Self-check sur copie temporaire — le registre réel n'est jamais touché.
    import shutil
    import tempfile

    tmp_dir = Path(tempfile.mkdtemp())
    tmp = tmp_dir / "registre.csv"
    nb_init = len(load_all())  # registre réel (avant bascule)
    shutil.copy(REGISTRY_PATH, tmp)
    REGISTRY_PATH = tmp  # noqa: F811 — bascule locale pour le test

    assert register_convention("TEST_A", "Client Test") == "created"
    assert register_convention("test_a", "Client Test 2", statut="Signe") == "updated"
    r = load_convention("TEST_A")
    assert r and r["client"] == "Client Test 2" and r["statut"] == "Signe"
    assert r["nb_modifications"] == "1"
    assert update_convention("TEST_A", statut="Signe") is None      # aucun changement
    assert update_convention("TEST_A", statut="Archive") is not None
    assert load_convention("INEXISTANT") is None
    assert len(load_all()) == nb_init + 1  # registre réel + TEST_A

    shutil.rmtree(tmp_dir, ignore_errors=True)
    print("Self-check OK")
