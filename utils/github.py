"""
GitHub API sync — persister les données sur GitHub.
"""
import os
import base64
import streamlit as st
import requests


def push_csv_to_github(csv_relpath, commit_msg):
    """Push CSV changes to GitHub via API pour persister sur Streamlit Cloud."""
    try:
        token = st.secrets.get("GITHUB_TOKEN", "")
        if not token:
            st.warning("GITHUB_TOKEN non configure dans Streamlit secrets - donnees non persistees sur GitHub", icon="⚠️")
            return False

        repo = "chkondali-dev/pilotage-b2b"
        branch = "main"
        url = f"https://api.github.com/repos/{repo}/contents/{csv_relpath}"
        headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}

        # Remonter d'un niveau depuis utils/ vers la racine du projet
        local_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), csv_relpath)
        if not os.path.exists(local_path):
            return False
        with open(local_path, "r", encoding="utf-8") as f:
            new_content = f.read()

        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            sha = r.json().get("sha", "")
        elif r.status_code == 404:
            sha = ""
        else:
            return False

        data = {
            "message": commit_msg,
            "content": base64.b64encode(new_content.encode("utf-8")).decode("utf-8"),
            "branch": branch,
        }
        if sha:
            data["sha"] = sha

        r = requests.put(url, headers=headers, json=data)
        return r.status_code in (200, 201)

    except Exception as e:
        st.warning(f"Synchro GitHub echouee: {e}", icon="⚠️")
        return False
