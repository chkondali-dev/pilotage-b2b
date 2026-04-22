"""
Script de configuration automatique pour la synchronisation GitHub
========================================================================
Ce script configure automatiquement tout ce qu'il faut pour synchroniser vos fichiers.
========================================================================

INSTRUCTIONS:
1. Ouvrir ce dossier dans VS Code ou terminal
2. Editer la section CONFIGURATION ci-dessous avec vos informations
3. Lancer: python setup_sync.py
========================================================================
"""

import os
import sys
import subprocess
from pathlib import Path

# ==================== CONFIGURATION ====================
# MODIFIEZ CES LIGNES AVEC VOS INFORMATIONS:

# Votre dossier contenant les fichiers Excel (2025)
LOCAL_DATA_FOLDER = r"C:\Users\hachk\OneDrive - Société Magasin Général (SMG)\Bureau\2025"

# Votre dossier local du projet Git
LOCAL_REPO_FOLDER = r"C:\Users\hachk\pilotage_b2b"

# Votre token GitHub (créer sur https://github.com/settings/tokens)
GITHUB_TOKEN = "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"

# ==================== LOGIQUE ====================

def run_command(cmd, cwd=None, check=True):
    """Exécute une commande système."""
    result = subprocess.run(
        cmd, shell=True, cwd=cwd, 
        capture_output=True, text=True
    )
    if check and result.returncode != 0:
        print(f"❌ Erreur: {result.stderr}")
    return result

def check_git():
    """Vérifie si git est installé."""
    result = run_command("git --version", check=False)
    return result.returncode == 0

def setup_git_config():
    """Configure git globalement."""
    print("\n⚙️ Configuration git...")
    run_command('git config --global user.email "sync@automatique.com"')
    run_command('git config --global user.name "Auto-Sync"')
    print("   ✅ git configuré")

def init_repo():
    """Initialise ou met à jour le repo."""
    repo_path = Path(LOCAL_REPO_FOLDER)
    
    if not repo_path.exists():
        print(f"\nINFO: Creation du dossier repo: {repo_path}")
        repo_path.mkdir(parents=True, exist_ok=True)
    
    # Créer le dossier 2025
    target_folder = repo_path / "2025"
    if not target_folder.exists():
        target_folder.mkdir(exist_ok=True)
    
    # Dire à l'utilisateur de copier les fichiers
    print(f"\nINFO: Copiez vos fichiers Excel dans ce dossier:")
    print(f"   {target_folder}")
    print(f"\n   Fichiers requis:")
    print(f"   - Factures ventes enregistrees VC (4).xlsx")
    print(f"   - Factures ventes enregistrees VC credit conso.xlsx")  
    print(f"   - Factures ventes enregistrees VC CONVENTION EDC.xlsx")
    print(f"   - TDC CONVENTION 1.xlsm")
    print(f"   - Code MAGASIN Business Central.xlsx")
    
    return True

def configure_git_remote():
    """Configure le remote avec le token."""
    print(f"\n🔗 Configuration du remote GitHub...")
    
    # Construire l'URL avec token
    remote_url = f"https://{GITHUB_TOKEN}@github.com/chkondali-dev/pilotage-b2b.git"
    
    os.chdir(LOCAL_REPO_FOLDER)
    
    # Vérifier si déjà un remote
    result = run_command("git remote -v", check=False)
    if "origin" in result.stdout:
        print("   -> Remote existant, mise a jour...")
        run_command(f'git remote set-url origin "{remote_url}"')
    else:
        print("   -> Creation du remote...")
        run_command(f'git remote add origin "{remote_url}"')
    
    print("   Remote configure")

def first_sync():
    """Première synchronisation."""
    print("\nINFO: Premier sync vers GitHub...")
    
    os.chdir(str(LOCAL_REPO_FOLDER))
    
    # Initialiser git si besoin
    git_dir = Path(LOCAL_REPO_FOLDER) / ".git"
    if not git_dir.exists():
        run_command("git init")
        run_command("git branch -M main")
    
    # Ajouter les fichiers
    print("   Ajout des fichiers...")
    run_command("git add -A")
    
    # Commit
    print("   Commit...")
    result = run_command('git commit -m "Sync initial"', check=False)
    if result.returncode == 0:
        print("   Commit cree")
    else:
        print(f"   INFO: {result.stdout[:100]}")
    
    # Push
    print("   Push vers GitHub...")
    result = run_command("git push -u origin main", check=False)
    if result.returncode == 0:
        print("   Sync termine!")

def main():
    print("=" * 60)
    print("CONFIGURATION SYNC AUTOMATIQUE")
    print("=" * 60)
    
    # Vérifier git
    print("\n🔍 Vérification de git...")
    if not check_git():
        print("❌ Git n'est pas installé!")
        print("   Installez-le depuis: https://git-scm.com")
        return
    
    print("   ✅ Git installé")
    
    # Configuration
    setup_git_config()
    
    # Copier les fichiers
    if not init_repo():
        return
    
    # Configurer remote
    if GITHUB_TOKEN == "ghp_VOTRE_TOKEN_ICI":
        print("\n⚠️ Token GitHub non configuré!")
        print("   Modifiez le fichier et ajoutez votre token")
        print("   Créez-le sur: https://github.com/settings/tokens")
        return
    
    configure_git_remote()
    
    # Premier sync
    first_sync()
    
    print("\n" + "=" * 60)
    print("✅ CONFIGURATION TERMINÉE!")
    print("=" * 60)
    print("\n📋 Prochaine étape:")
    print("   Programmer une tâche Windows pour exécuter sync_github.py chaque jour")

if __name__ == "__main__":
    main()