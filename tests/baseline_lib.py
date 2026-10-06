"""
Baseline Phase 0 — logique partagee entre le generateur (make_baseline.py)
et le test de non-regression (test_baseline.py).

Regles figees (mission) :
  - date de reference fixe  : 2026-10-05 (KPI date-a-date / inactivite)
  - seuil d'inactivite      : SEUILS["inactivite_jours"] (defaut data/config.py)
  - filtre mois             : vide (annee complete)
  - filtre convention       : "Tous"
  - aucune donnee reseau    : lecture du snapshot tests/fixtures/ (mock de
                              data.loader._fetch et data.loader.load_crm)
  - aucun appel a push_csv_to_github
"""
from __future__ import annotations

import json
import sys
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch
from urllib.parse import unquote

import pandas as pd

TESTS_DIR = Path(__file__).resolve().parent
ROOT_DIR = TESTS_DIR.parent
FIXTURES_DIR = TESTS_DIR / "fixtures"
BASELINE_PATH = TESTS_DIR / "baseline.json"

# Date de reference fixe du snapshot (voir AUDIT_PHASE0.md).
REF_DATE = "2026-10-05"

TYPES_VENTE = ["Global", "Convention", "Credit conso", "Credit particulier"]
ANNEES = [2025, 2026]

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


# ── Environnement hors-ligne ────────────────────────────────────

def _fetch_local(url: str) -> bytes:
    """Remplace data.loader._fetch : lit le snapshot local (aucun reseau)."""
    name = unquote(str(url).rsplit("/", 1)[-1])
    path = FIXTURES_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"fixture absente : {name}")
    return path.read_bytes()


def _frozen_timestamp_cls():
    """Classe Timestamp figee a REF_DATE (today/now)."""
    ref = pd.Timestamp(REF_DATE)

    class _FrozenTimestamp(pd.Timestamp):
        @classmethod
        def today(cls):
            return cls(ref)

        @classmethod
        def now(cls, tz=None):
            base = cls(ref)
            return base.tz_localize(tz) if tz else base

    return _FrozenTimestamp


@contextmanager
def offline_env():
    """Patch data.loader (lecture locale, pas de CRM) + horloge figee."""
    import data.loader as loader

    with patch.object(loader, "_fetch", _fetch_local), \
            patch.object(loader, "load_crm", lambda: None), \
            patch.object(pd, "Timestamp", _frozen_timestamp_cls()):
        yield


def load_prepared() -> tuple:
    """Pipeline reel : load_all_data (offline) puis prepare_data."""
    from data.loader import load_all_data
    from data.transforms import prepare_data

    return prepare_data(load_all_data())


# ── Decoupage « Type de vente » (identique a app.py l.177-190) ──

def slice_type_vente(type_sel: str, df_vc, df_credit, df_credit_part) -> pd.DataFrame:
    """Reproduit le filtre Type de vente du dashboard (source : app.py)."""
    if type_sel == "Global":
        out = df_vc.copy()
        if not df_credit.empty:
            out = pd.concat([out, df_credit], ignore_index=True)
        if not df_credit_part.empty:
            out = pd.concat([out, df_credit_part], ignore_index=True)
        return out
    if type_sel == "Convention":
        return df_vc.copy()
    if type_sel == "Credit conso":
        return df_credit.copy() if not df_credit.empty else pd.DataFrame()
    if type_sel == "Credit particulier":
        return df_credit_part.copy() if not df_credit_part.empty else pd.DataFrame()
    raise ValueError(f"Type de vente inconnu : {type_sel}")


# ── Calcul des indicateurs de la baseline ──────────────────────

def compute_baseline(prepared: tuple) -> dict:
    """
    Indicateurs affiches par le dashboard (Vue Executive, filtres par defaut)
    pour 4 types de vente x 2025/2026 :
      ca_n, ca_n1          : ca_sum_date_to_date (date a date)
      nb_factures          : volumes_panier["Nb N"] (ventes positives)
      panier_moyen         : volumes_panier["Panier N"]
      conventions_actives  : nunique « Nom » sur l'annee (= nb_actives app.py)
      ca_a_risque          : somme « CA N-1 » des inactive_conventions (seuil defaut)
    """
    from data.config import SEUILS
    from metrics.kpi import (
        ca_sum_date_to_date,
        inactive_conventions,
        volumes_panier,
    )

    seuil = int(SEUILS["inactivite_jours"])
    df_vc, df_credit, _df_edc, _df_conv, _code, df_credit_part, *_ = prepared

    out: dict = {}
    for type_sel in TYPES_VENTE:
        df_f = slice_type_vente(type_sel, df_vc, df_credit, df_credit_part)
        by_year: dict = {}
        for annee in ANNEES:
            ca_n, ca_n1, _evo = ca_sum_date_to_date(df_f, annee, annee - 1, None)
            vol = volumes_panier(df_f, annee, None)
            actives = (
                df_f[df_f["Année"] == annee]["Nom"].dropna().nunique()
                if "Nom" in df_f.columns else 0
            )
            inac = inactive_conventions(df_f, seuil, annee_n=annee)
            ca_risque = (
                float(inac["CA N-1"].sum())
                if (not inac.empty and "CA N-1" in inac.columns) else 0.0
            )
            by_year[str(annee)] = {
                "ca_n": round(float(ca_n), 2),
                "ca_n1": round(float(ca_n1), 2),
                "nb_factures": int(vol["Nb N"]),
                "panier_moyen": float(vol["Panier N"]),
                "conventions_actives": int(actives),
                "ca_a_risque": round(ca_risque, 2),
            }
        out[type_sel] = by_year

    return {
        "meta": {
            "date_reference": REF_DATE,
            "seuil_inactivite_jours": seuil,
            "filtre_mois": "vide",
            "filtre_convention": "Tous",
            "annees": ANNEES,
            "types_vente": TYPES_VENTE,
            "snapshot": "tests/fixtures/",
            "comment": (
                "Baseline Phase 0 — generee par tests/make_baseline.py. "
                "Toute evolution de ces chiffres exige un accord explicite."
            ),
        },
        "types": out,
    }


def compute_or_die() -> dict:
    with offline_env():
        return compute_baseline(load_prepared())


def main() -> None:
    data = compute_or_die()
    BASELINE_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Baseline ecrite : {BASELINE_PATH}")
    for t, years in data["types"].items():
        for a, k in years.items():
            print(f"  {t:<18} {a}: ca_n={k['ca_n']:>14,.0f} ca_n1={k['ca_n1']:>14,.0f} "
                  f"factures={k['nb_factures']:>6} panier={k['panier_moyen']:>8,.0f} "
                  f"actives={k['conventions_actives']:>5} risque={k['ca_a_risque']:>12,.0f}")


if __name__ == "__main__":
    main()
