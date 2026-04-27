"""
Sync GitHub - Synchronisation automatique des fichiers
使用方法: python sync_github.py
环境变量: GITHUB_TOKEN=votre_token
"""

import os
import sys
import subprocess
from datetime import datetime

TARGET_FOLDER = r"C:\Users\hachk\pilotage_b2b"

def get_token():
    """Recupere le token depuis la variable d'environnement"""
    token = os.environ.get('GITHUB_TOKEN')
    if not token:
        print("ERREUR: Definissez GITHUB_TOKEN")
        print("   Windows: set GITHUB_TOKEN=votre_token")
        sys.exit(1)
    return token

def sync_files():
    print("=" * 60)
    print("SYNC GITHUB - Synchronisation automatique")
    print("=" * 60)
    
    token = get_token()
    os.chdir(TARGET_FOLDER)
    
    subprocess.run(['git', 'config', '--global', 'user.email', 'sync@automatique.com'], capture_output=True)
    subprocess.run(['git', 'config', '--global', 'user.name', 'Auto-Sync'], capture_output=True)
    
    remote_url = f"https://chkondali-dev:{token}@github.com/chkondali-dev/pilotage-b2b.git"
    subprocess.run(['git', 'remote', 'set-url', 'origin', remote_url], capture_output=True)
    
    subprocess.run(['git', 'add', '-A'], capture_output=True)
    
    commit_msg = f"Auto-sync {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    result = subprocess.run(['git', 'commit', '-m', commit_msg], capture_output=True, text=True)
    
    if "nothing to commit" in result.stdout:
        print("Rien a synchroniser - tout est a jour")
    else:
        print("Commit cree")
    
    result = subprocess.run(['git', 'push', 'origin', 'main'], capture_output=True, text=True)
    
    if result.returncode == 0:
        print("Synchronise vers GitHub!")
    else:
        print(f"Erreur: {result.stderr}")

if __name__ == "__main__":
    sync_files()
