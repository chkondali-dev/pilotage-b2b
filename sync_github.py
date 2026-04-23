"""
Sync GitHub - Synchronisation automatique des fichiers
"""

import os
import subprocess
from datetime import datetime
from pathlib import Path

LOCAL_FOLDER = r"C:\Users\hachk\OneDrive - Societe Magasin General (SMG)\Documents\hamadi\grands compte\hamadi\dashbord convention\table vente\2025"
TARGET_FOLDER = r"C:\Users\hachk\pilotage_b2b"
COMMIT_MESSAGE = f"Auto-sync {datetime.now().strftime('%Y-%m-%d %H:%M')}"

def get_token():
    token = os.environ.get('GITHUB_TOKEN')
    if not token:
        print("ERREUR: Definissez GITHUB_TOKEN")
        print("   set GITHUB_TOKEN=votre_token")
        sys.exit(1)
    return token

def sync_files():
    import shutil
    
    print("=" * 60)
    print("SYNC GITHUB - Synchronisation automatique")
    print("=" * 60)
    
    target_2025 = os.path.join(TARGET_FOLDER, "2025")
    os.makedirs(target_2025, exist_ok=True)
    
    files_copied = 0
    for f in Path(LOCAL_FOLDER).glob("*"):
        if f.is_file() and f.suffix in ['.xlsx', '.xlsm', '.csv']:
            dest = Path(target_2025) / f.name
            shutil.copy2(f, dest)
            print(f"  Copie: {f.name}")
            files_copied += 1
    
    print(f"\n{files_copied} fichiers copies")
    
    os.chdir(TARGET_FOLDER)
    
    subprocess.run(['git', 'config', '--global', 'user.email', 'sync@automatique.com'], capture_output=True)
    subprocess.run(['git', 'config', '--global', 'user.name', 'Auto-Sync'], capture_output=True)
    
    token = get_token()
    remote_url = f"https://chkondali-dev:{token}@github.com/chkondali-dev/pilotage-b2b.git"
    subprocess.run(['git', 'remote', 'set-url', 'origin', remote_url], capture_output=True)
    
    subprocess.run(['git', 'add', '-A'], capture_output=True)
    
    result = subprocess.run(['git', 'commit', '-m', COMMIT_MESSAGE], capture_output=True, text=True)
    if "nothing to commit" not in result.stdout and result.returncode == 0:
        print("  Commit cree")
    
    result = subprocess.run(['git', 'push', 'origin', 'main'], capture_output=True, text=True)
    if result.returncode == 0:
        print("  Synchronise vers GitHub!")
    else:
        print(f"  Erreur push: {result.stderr}")

if __name__ == "__main__":
    sync_files()