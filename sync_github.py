"""
Script de synchronisation automatique vers GitHub
================================================================================
Ce script surveille un dossier local et pousse automatiquement les fichiers vers GitHub.
================================================================================

UTILISATION:
    python sync_github.py
    
CONFIGURATION:
    1. Créer un Personal Access Token sur GitHub:
       - Aller sur https://github.com/settings/tokens
       - Générer un nouveau token (repo scope)
       - Copier le token
       
    2. Configurer les variables d'environnement:
       - GITHUB_TOKEN:Votre token GitHub
       - GITHUB_REPO: "votre_username/votre_repo" (ex: chkondali-dev/pilotage-b2b)
       - LOCAL_FOLDER: "C:/Users/hachk/OneDrive - Société Magasin Général (SMG)/Bureau/2025"
       
    3. Programmer l'exécution ( Windows Task Scheduler):
       - Tâche planifiée chaque matin à 8h
"""

import os
import sys
import time
import subprocess
from datetime import datetime
from pathlib import Path

# ==================== CONFIGURATION ====================
# À MODIFIER SELON VOS PARAMÈTRES
LOCAL_FOLDER = r"C:\Users\hachk\OneDrive - Société Magasin Général (SMG)\Documents\hamadi\grands compte\hamadi\dashbord convention\table vente\2025"
GITHUB_REPO = "chkondali-dev/pilotage-b2b"
TARGET_FOLDER = r"C:\Users\hachk\pilotage_b2b\2025"
COMMIT_MESSAGE = f"Auto-sync {datetime.now().strftime('%Y-%m-%d %H:%M')}"

# Extensions de fichiers à synchroniser
FILE_EXTENSIONS = ['.xlsx', '.xlsm', '.csv']

# ==================== FONCTIONS ====================

def get_github_token():
    """Récupère le token depuis les variables d'environnement."""
    token = os.environ.get('GITHUB_TOKEN')
    if not token:
        print("❌ ERREUR: Variable d'environnement GITHUB_TOKEN non définie")
        print("   Configurez-la avec: set GITHUB_TOKEN=votre_token")
        sys.exit(1)
    return token

def get_local_files(folder_path):
    """Liste tous les fichiers Excel/CSV dans le dossier local."""
    folder = Path(folder_path)
    if not folder.exists():
        print(f"❌ ERREUR: Dossier non trouvé: {folder_path}")
        sys.exit(1)
    
    files = []
    for ext in FILE_EXTENSIONS:
        files.extend(folder.glob(f"*{ext}"))
    
    return {f.name: f for f in files}

def get_github_files(repo, token):
    """Récupère la liste des fichiers depuis GitHub."""
    import requests
    
    url = f"https://api.github.com/repos/{repo}/contents/2025"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 200:
            return {f['name']: f for f in response.json() if f['name'].endswith(tuple(FILE_EXTENSIONS))}
        elif response.status_code == 404:
            return {}  # Dossier vide ou n'existe pas
        else:
            print(f"⚠️ Erreur GitHub API: {response.status_code}")
            return {}
    except Exception as e:
        print(f"⚠️ Erreur connexion: {e}")
        return {}

def upload_file(file_path, repo, token):
    """Upload un fichier vers GitHub."""
    import base64
    import requests
    
    file_name = os.path.basename(file_path)
    url = f"https://api.github.com/repos/{repo}/contents/2025/{file_name}"
    
    # Lire le contenu du fichier
    with open(file_path, 'rb') as f:
        content = f.read()
    
    # Encoder en base64
    content_b64 = base64.b64encode(content).decode('utf-8')
    
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json"
    }
    
    data = {
        "message": COMMIT_MESSAGE,
        "content": content_b64,
        "branch": "main"
    }
    
    try:
        response = requests.put(url, headers=headers, json=data, timeout=60)
        if response.status_code in [200, 201]:
            return True, response.json().get('content', {}).get('html_url', '')
        else:
            print(f"   ⚠️ Erreur upload {file_name}: {response.status_code}")
            return False, response.text
    except Exception as e:
        print(f"   ⚠️ Exception: {e}")
        return False, str(e)

def run_git_sync(folder_path, repo):
    """Metthode alternative avec git CLI."""
    import shutil
    
    # Copier les fichiers vers le repo local
    print(f"\n📂 Copie des fichiers vers le repo local...")
    
    # Creer le dossier cible si besoin
    os.makedirs(TARGET_FOLDER, exist_ok=True)
    
    # Copier tous les fichiers
    files_copied = 0
    for f in Path(folder_path).glob("*"):
        if f.is_file() and f.suffix in ['.xlsx', '.xlsm', '.csv']:
            dest = Path(TARGET_FOLDER) / f.name
            shutil.copy2(f, dest)
            print(f"   -> {f.name}")
            files_copied += 1
    
    print(f"   {files_copied} fichiers copies")
    
    # Se deplacer dans le repo
    os.chdir(TARGET_FOLDER)
    
    # Configurer git si besoin
    subprocess.run(['git', 'config', '--global', 'user.email', 'sync@automatique.com'], capture_output=True)
    subprocess.run(['git', 'config', '--global', 'user.name', 'Auto-Sync'], capture_output=True)
    
    # Ajouter tous les fichiers
    result = subprocess.run(['git', 'add', '-A'], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"⚠️ git add error: {result.stderr}")
        return
    
    # Commit avec message
    result = subprocess.run(['git', 'commit', '-m', COMMIT_MESSAGE], capture_output=True, text=True)
    if "nothing to commit" in result.stdout or result.returncode == 0:
        print("✅ Rien à synchroniser - fichiers déjà à jour")
    else:
        print(f"✅ Commit créé: {result.stdout[:100]}")
    
    # Pousser vers GitHub
    result = subprocess.run(['git', 'push', 'origin', 'main'], capture_output=True, text=True)
    if result.returncode == 0:
        print("✅ Synchronisé vers GitHub!")
    else:
        print(f"⚠️ Push error: {result.stderr}")

def main():
    """Point d'entrée principal."""
    print("=" * 60)
    print("🚀 SYNC GITHUB - Synchronisation automatique")
    print("=" * 60)
    print(f"📁 Dossier: {LOCAL_FOLDER}")
    print(f"📦 Repo: {GITHUB_REPO}")
    print(f"🕐 Date: {datetime.now()}")
    print("=" * 60)
    
    # Vérifier que le dossier existe
    if not os.path.exists(LOCAL_FOLDER):
        print(f"❌ ERREUR: Le dossier n'existe pas: {LOCAL_FOLDER}")
        print("   Créez le dossier ou modifiez la variable LOCAL_FOLDER dans le script")
        sys.exit(1)
    
    # Option 1: Avec git CLI (recommandé si git installé)
    try:
        subprocess.run(['git', '--version'], capture_output=True, check=True)
        print("\n✅ Git détecté - utilisation méthode git")
        run_git_sync(LOCAL_FOLDER, GITHUB_REPO)
    except:
        # Option 2: API GitHub directe
        print("\n⚠️ Git non détecté - utilisation API GitHub")
        token = get_github_token()
        
        print("\n📤 Upload des fichiers...")
        files = get_local_files(LOCAL_FOLDER)
        
        if not files:
            print("   Aucun fichier à synchroniser")
        else:
            for name, path in files.items():
                print(f"   → {name}")
                success, msg = upload_file(str(path), GITHUB_REPO, token)
                if success:
                    print(f"      ✅ OK")
                else:
                    print(f"      ⚠️ {msg[:50]}")
        
        print("\n✅ Synchronisation terminée!")

if __name__ == "__main__":
    main()