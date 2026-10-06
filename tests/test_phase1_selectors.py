"""Phase 1.1 — sélecteurs d'année dérivés (jamais figés, jamais de ValueError)."""
import pytest

from data.config import annees_selecteur_principal, annees_selecteur_rapport


def test_principal_derive_des_donnees():
    """Les années viennent des données, en ordre décroissant (défaut = la plus récente)."""
    assert annees_selecteur_principal({2024, 2025, 2026}, 2026) == [2026, 2025, 2024]


def test_principal_accepte_floats_nan_free():
    """df['Année'].dropna().unique() renvoie des float sous pandas."""
    assert annees_selecteur_principal([2026.0, 2025.0, 2026.0], 2026) == [2026, 2025]


def test_principal_sans_donnees_repli_annee_courante():
    """Aucune donnée → [année courante] : pas de crash, l'écran d'erreur suit."""
    assert annees_selecteur_principal(set(), 2027) == [2027]
    assert len(annees_selecteur_principal([], None)) == 1  # datetime.now().year


def test_rapport_jamais_de_valueerror_en_2027():
    """Le bug de janvier 2027 : l'ancien .index(default_year) levait ValueError."""
    opts, idx = annees_selecteur_rapport([2024, 2025, 2026], 2027)
    assert 2027 in opts
    assert opts[idx] == 2027


def test_ancien_pattern_effectivement_casse():
    """Le pattern historique lève bien ValueError en 2027 (non régressé)."""
    with pytest.raises(ValueError):
        [2023, 2024, 2025, 2026].index(2027)


def test_rapport_options_donnees_union_courante():
    opts, idx = annees_selecteur_rapport({2024, 2025, 2026}, 2026)
    assert opts == [2024, 2025, 2026]
    assert opts[idx] == 2026
    # défaut toujours présent, ordre conservé (croissant, comme l'ancien écran)
    assert opts == sorted(opts)
