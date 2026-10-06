"""Phase 1.4 & 1.6 — clés API et nettoyages (contrôles de source)."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP = (ROOT / "app.py").read_text(encoding="utf-8")


# ── 1.4 — clé API jamais en ligne de commande ──────────────────

def test_1_4_pas_de_cle_en_ligne_de_commande():
    assert "--api-key" not in APP


def test_1_4_cle_transportee_par_lenvironnement():
    """LLM_API_KEY reste injectée dans l'environnement du sous-processus."""
    assert 'env["LLM_API_KEY"] = api_key' in APP


def test_1_4_monthly_report_resout_la_cle_depuis_lenvironnement():
    mr = (ROOT / "monthly_report.py").read_text(encoding="utf-8")
    assert "args.api_key or _GROQ_API_KEY" in mr
    # _GROQ_API_KEY = os.getenv("LLM_API_KEY", ...)
    assert 'os.getenv("LLM_API_KEY"' in mr


# ── 1.6 — nettoyages ───────────────────────────────────────────

def test_1_6_plus_de_df_vc_in_dir():
    assert '"df_vc" in dir()' not in APP


def test_1_6_un_seul_import_plotly_express():
    """L'import local redondant de l'onglet Conventions encours est supprimé."""
    assert APP.count("import plotly.express as px") == 1
    assert "import plotly.express as px" in APP  # l'import global reste


# Motif exact de la mission : `except:` (bare) ou `except Exception...:` avec corps `pass`.
# Les `except ValueError:` / `except (TypeError, ValueError):` de flux normal
# (metrics/kpi.py evol_pct, data/transforms.py map_store_name) ne sont pas des
# swallows silencieux : ils retournent NaN par conception — hors périmètre.
_SILENT = re.compile(r"except\s*(?:Exception[^:\n]*)?:\s*\r?\n\s+pass\b")


def test_1_6_aucun_except_pass_silencieux():
    """Plus aucun `except: pass` ni `except Exception: pass` dans app.py."""
    assert not _SILENT.search(APP)


def test_1_6_autres_fichiers_sans_except_pass():
    cibles = ["monthly_report.py", "send_report.py", "trend_narrative.py",
              "data/loader.py", "data/transforms.py", "metrics/kpi.py",
              "utils/github.py", "ui/components.py", "charts/factory.py"]
    for rel in cibles:
        txt = (ROOT / rel).read_text(encoding="utf-8")
        assert not _SILENT.search(txt), rel
