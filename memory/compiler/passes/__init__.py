"""passes — Registre et autodiscover des passes de compilation.

Chaque module dans ce repertoire est importe automatiquement,
ce qui declenche les decorateurs @register_pass.
"""

import importlib
import pkgutil
import sys
from pathlib import Path


def discover_passes():
    """Importe tous les modules du package passes/ pour declarer leurs @register_pass."""
    pkg_dir = Path(__file__).parent
    pkg_name = __name__

    for importer, modname, ispkg in pkgutil.iter_modules([str(pkg_dir)]):
        if modname == "__init__" or modname.startswith("_"):
            continue
        full_name = f"{pkg_name}.{modname}"
        if full_name not in sys.modules:
            importlib.import_module(full_name)


# Auto-decouverte au chargement du package
discover_passes()
