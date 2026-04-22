"""
Script de creation des taches planifiees pour sync automatique
========================================================================
Cree 3 taches: 9h, 10h, 12h

UTILISATION:
    python setup_tasks.py
========================================================================
"""

import subprocess
import os

# Chemins
BATCH_FILE = r"C:\Users\hachk\pilotage_b2b\sync_b2b.bat"
PYTHON_FILE = r"C:\Users\hachk\pilotage_b2b\sync_github.py"

# Heures de sync
HOURS = ["09", "10", "12"]

def create_task(hour):
    """Cree une tache planifiee."""
    task_name = f"Sync_B2B_{hour}H"
    time = f"{hour}:00"
    
    # Commande schtasks
    cmd = f'schtasks /create /tn "{task_name}" /tr "python \\"{PYTHON_FILE}\\"" /sc daily /st {time} /f'
    
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode == 0:
        print(f"  Tache creee: {task_name} a {time}")
    else:
        print(f"  Erreur {task_name}: {result.stderr[:100]}")

def delete_tasks():
    """Supprime les anciennes taches."""
    for hour in HOURS:
        task_name = f"Sync_B2B_{hour}H"
        cmd = f'schtasks /delete /tn "{task_name}" /f'
        subprocess.run(cmd, shell=True, capture_output=True)

def main():
    print("=" * 50)
    print("CREATION DES TACHES PLANIFIEES")
    print("=" * 50)
    print(f"\n1. Suppression des anciennes taches...")
    delete_tasks()
    
    print(f"\n2. Creation des nouvelles taches...")
    for hour in HOURS:
        create_task(hour)
    
    print("\n" + "=" * 50)
    print("TACHES CREES!")
    print("Heures: 9h00, 10h00, 12h00")
    print("=" * 50)

if __name__ == "__main__":
    main()