"""
GitHub API sync — persister les données sur GitHub.

Chaque appel retourne un statut explicite (Phase 1.2) :
  {"ok": True,  "status": "synced", "detail": ...}
  {"ok": False, "status": "no_token" | "no_local_file" | "remote_changed"
                 | "http_error" | "exception", "detail": ...}
Aucun token n'est jamais retourné ni journalisé.
"""
import base64
import hashlib
from pathlib import Path

import requests

# Racine du dépôt (surchargeable en test pour ne jamais toucher le dépôt réel).
REPO_ROOT = Path(__file__).resolve().parent.parent


def git_blob_sha1(data: bytes) -> str:
    """SHA-1 « blob » git du contenu — identique au champ sha de l'API contents."""
    h = hashlib.sha1()
    h.update(b"blob " + str(len(data)).encode("ascii") + b"\0" + data)
    return h.hexdigest()


def file_sha(path) -> str | None:
    """git_blob_sha1 du fichier local (observé à la LECTURE), None si absent."""
    p = Path(path)
    if not p.exists():
        return None
    return git_blob_sha1(p.read_bytes())


def _get_token() -> str:
    """GITHUB_TOKEN depuis st.secrets (vide si absent/inaccessible)."""
    try:
        import streamlit as st
        return str(st.secrets.get("GITHUB_TOKEN", "") or "")
    except Exception:
        return ""


def push_csv_to_github(csv_relpath, commit_msg, base_sha=None) -> dict:
    """Pousse un fichier du dépôt sur GitHub (branche main) avec statut explicite.

    ``base_sha`` = sha blob observé au moment de la lecture du fichier local.
    Si le sha distant actuel en diffère, le fichier distant a changé depuis la
    lecture (autre session / déploiement) : l'écrasement est REFUSÉ
    (pas d'overwrite silencieux). Sans ``base_sha``, pas de comparaison possible.
    """
    try:
        token = _get_token()
        if not token:
            return {"ok": False, "status": "no_token",
                    "detail": "GITHUB_TOKEN absent de st.secrets — "
                              "données non persistées sur GitHub"}

        repo = "chkondali-dev/pilotage-b2b"
        branch = "main"
        url = f"https://api.github.com/repos/{repo}/contents/{csv_relpath}"
        headers = {"Authorization": f"token {token}",
                   "Accept": "application/vnd.github.v3+json"}

        local_path = REPO_ROOT / csv_relpath
        if not local_path.exists():
            return {"ok": False, "status": "no_local_file", "detail": str(local_path)}
        new_content = local_path.read_bytes()

        r = requests.get(url, headers=headers, timeout=30)
        if r.status_code == 200:
            remote_sha = r.json().get("sha", "")
        elif r.status_code == 404:
            remote_sha = None  # fichier absent du dépôt distant
        else:
            return {"ok": False, "status": "http_error",
                    "detail": f"GET contents: HTTP {r.status_code}"}

        if base_sha is not None and remote_sha != base_sha:
            return {"ok": False, "status": "remote_changed",
                    "detail": "fichier distant modifié depuis la lecture "
                              f"(attendu {base_sha[:7] if base_sha else 'absent'}, "
                              f"distant {remote_sha[:7] if remote_sha else 'absent'}) "
                              "— écrasement refusé"}

        data = {"message": commit_msg,
                "content": base64.b64encode(new_content).decode("ascii"),
                "branch": branch}
        if remote_sha:
            data["sha"] = remote_sha

        r = requests.put(url, headers=headers, json=data, timeout=30)
        if r.status_code in (200, 201):
            return {"ok": True, "status": "synced", "detail": f"HTTP {r.status_code}"}
        return {"ok": False, "status": "http_error",
                "detail": f"PUT contents: HTTP {r.status_code}"}

    except Exception as e:
        return {"ok": False, "status": "exception", "detail": str(e)}

