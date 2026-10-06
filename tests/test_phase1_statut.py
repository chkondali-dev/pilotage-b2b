"""Phase 1.3 — colonne « Statut » : liste fermée lue depuis data/config.py."""
import csv
import io
from pathlib import Path

from data.config import STATUTS_CONVENTION

ROOT = Path(__file__).resolve().parent.parent


def test_liste_complete_et_sans_doublon():
    assert len(STATUTS_CONVENTION) == len(set(STATUTS_CONVENTION))
    for s in ("Prospection", "Negociation", "En cours", "Finalisation",
              "Signe", "Finalise", "Refuse", "Archive"):
        assert s in STATUTS_CONVENTION, f"statut manquant : {s}"


def test_valeurs_existantes_dans_le_registre_sont_dans_la_liste():
    """Toute valeur déjà présente dans le CSV reste sélectionnable (aucune migration forcée)."""
    rows = list(csv.DictReader(
        io.open(ROOT / "data" / "conventions_signees.csv", encoding="utf-8"),
        delimiter=";"))
    valeurs = sorted({str(r.get("statut", "")).strip() for r in rows} - {""})
    hors = sorted(set(valeurs) - set(STATUTS_CONVENTION))
    assert hors == [], f"valeurs du registre hors de la liste fermée : {hors}"


def test_app_utilise_selectboxcolumn_depuis_config():
    src = (ROOT / "app.py").read_text(encoding="utf-8")
    assert "st.column_config.SelectboxColumn(" in src
    assert "options=STATUTS_CONVENTION" in src
    assert 'TextColumn("Statut"' not in src, "la colonne Statut doit être une liste fermée"
