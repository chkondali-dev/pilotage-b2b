"""
Test de non-regression — baseline Phase 0 (critere d'acceptation 0.5).

Recalcule les indicateurs affiches par le dashboard (4 types de vente x
2025/2026, filtres par defaut) sur le snapshot tests/fixtures/ et les
compare a tests/baseline.json.

Tout ecart > tolerance = evolution de chiffre = echec du test.
"""
import json

import pytest

from baseline_lib import (
    ANNEES,
    BASELINE_PATH,
    TYPES_VENTE,
    compute_baseline,
)

# Cles attendues pour chaque combinaison type x annee.
INDICATEURS = [
    "ca_n",
    "ca_n1",
    "nb_factures",
    "panier_moyen",
    "conventions_actives",
    "ca_a_risque",
]

# Tolerance monetaire (arrondis de sommation flottantes uniquement).
TOL = 0.01


def test_baseline_file_exists():
    assert BASELINE_PATH.exists(), (
        "tests/baseline.json absent — regenerer : python tests/make_baseline.py "
        "(uniquement apres validation d'un changement de chiffres)"
    )


def test_baseline_meta_matches_rules(baseline):
    """Parametres figes par la mission : date, seuil defaut, mois vide, Tous."""
    from data.config import SEUILS

    meta = baseline["meta"]
    assert meta["date_reference"] == "2026-10-05"
    assert meta["seuil_inactivite_jours"] == SEUILS["inactivite_jours"] == 60
    assert meta["filtre_mois"] == "vide"
    assert meta["filtre_convention"] == "Tous"


def test_baseline_covers_all_types_and_years(baseline):
    """Couverture : 4 types de vente, 2 annees, 6 indicateurs."""
    assert baseline["meta"]["types_vente"] == TYPES_VENTE
    assert baseline["meta"]["annees"] == ANNEES
    for type_sel in TYPES_VENTE:
        assert type_sel in baseline["types"], f"type manquant : {type_sel}"
        for annee in ANNEES:
            block = baseline["types"][type_sel].get(str(annee))
            assert block is not None, f"combinaison manquante : {type_sel}/{annee}"
            missing = [k for k in INDICATEURS if k not in block]
            assert not missing, f"indicateurs manquants {type_sel}/{annee} : {missing}"


def test_kpis_unchanged_vs_baseline(baseline, prepared):
    """COEUR de la non-regression : recalcul = baseline, chiffre pour chiffre."""
    actual = compute_baseline(prepared)

    ecarts = []
    for type_sel in TYPES_VENTE:
        for annee in ANNEES:
            key = str(annee)
            exp = baseline["types"][type_sel][key]
            got = actual["types"][type_sel][key]
            for ind in INDICATEURS:
                e, g = exp[ind], got[ind]
                if isinstance(e, int) and not isinstance(e, bool):
                    ok = int(g) == int(e)
                else:
                    ok = abs(float(g) - float(e)) <= TOL
                if not ok:
                    ecarts.append(
                        f"{type_sel}/{key}/{ind}: baseline={e} recalcule={g}"
                    )
    assert not ecarts, (
        "Chiffres modifies vs tests/baseline.json :\n  " + "\n  ".join(ecarts)
    )


def test_seuil_slider_default_unchanged():
    """Le slider d'inactivite doit rester au defaut SEUILS (parametre fige)."""
    from data.config import SEUILS

    assert SEUILS["inactivite_jours"] == 60
