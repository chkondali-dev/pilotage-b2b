# Refonte : Separation donnees / app + auto-alimentation conventions

## TL;DR

> **Quick Summary**: Refactor tabs[6] ("Conventions encours") pour separer le CSV des donnees du code applicatif (dossier data/), automatiser la creation des projets, et remplacer la suppression par un archivage.
>
> **Deliverables**:
> - data/conventions_signees.csv -- donnees deplacees hors de la racine
> - app.py (tabs[6]) -- chemins mis a jour, formulaire auto-alimente, archivage
> - Filtre "Archives" pour masquer/afficher les projets archives

---

## Context

### Original Request
"J'ai constate beaucoup de problemes. Je propose que chaque creation d'une nouvelle convention alimente une base simple (tableau) avec le nom, modele de contrat, date debut, compteur delai, statut, nombre de modifications."

### Interview Summary
**Key Discussions**:
- **Probleme principal**: Donnees (CSV) et app melangees dans le meme dossier -> besoin de separation
- **Declencheur creation**: Nouveau projet identifie -> ligne creee automatiquement dans la table
- **Stockage**: CSV structure dans dossier data/ a la racine du repo (meme repo)
- **Structure**: Memes colonnes qu'aujourd'hui (code, client, scenario, garantie, statut, date_debut_prospection, date_signature, nb_modifications, notes)
- **Alimentation**: Formulaire "Ajouter" auto-remplit date_debut = aujourd'hui, nb_modifications = 0
- **Suppression**: Remplacee par archivage (statut = "Archive")
- **Delai**: Calcule automatiquement (date_signature - date_debut, ou aujourd'hui - date_debut si pas de signature)

---

## Work Objectives

### Core Objective
Separer les donnees du code, automatiser la creation des projets conventions, et remplacer la suppression physique par un archivage logique.

### Must Have
- [ ] CSV deplace dans data/ et lu depuis ce chemin
- [ ] Suppression remplacee par archivage (bouton "Archiver" au lieu de "Supprimer")
- [ ] Formulaire auto-alimente (date_debut = today, nb_modifications = 0)
- [ ] Filtre statut inclut "Archive" et fonctionne

### Must NOT Have (Guardrails)
- **Ne pas** modifier les autres tabs (0-5, 7)
- **Ne pas** ajouter de nouvelles colonnes au CSV
- **Ne pas** changer le format du CSV (separateur ;, encodage UTF-8)
- **Ne pas** ajouter de nouveaux graphiques ou KPIs
- **Ne pas** refactorer le code au-dela de tabs[6]

---

## Verification Strategy
> **ZERO HUMAN INTERVENTION** - ALL verification is agent-executed.

### Test Decision
- **Infrastructure exists**: NO
- **Automated tests**: None
- **Agent-Executed QA**: ALWAYS - chaque tache a ses scenarios de validation

---

## TODOs

- [ ] 1. Creer data/ et deplacer conventions_signees.csv

  **What to do**:
  - Creer le dossier data/ a la racine du projet
  - Copier conventions_signees.csv -> data/conventions_signees.csv
  - Verifier que le fichier deplace a le meme contenu, meme separateur ;, meme encodage UTF-8
  - Le fichier original a la racine doit etre conserve

  **Must NOT do**:
  - Ne pas modifier le contenu du CSV
  - Ne pas renommer les colonnes

  **Parallelization**:
  - Can Run In Parallel: YES (Wave 1)
  - Blocks: Tasks 2, 4
  - Blocked By: None

  **Acceptance Criteria**:
  - [ ] data/conventions_signees.csv existe et est lisible
  - [ ] Le contenu est identique a l'original (memes 5 lignes + header)

  **QA Scenarios**:
  `
  Scenario: Verifier deplacement du CSV
    Tool: Bash (python)
    Steps:
      1. Lire data/conventions_signees.csv avec pd.read_csv(sep=";", encoding="utf-8")
      2. Verifier que le DataFrame a 5 lignes et 9 colonnes
    Expected Result: 5 lignes, 9 colonnes, pas d'erreur
    Evidence: .omo/evidence/task-1-csv-verification.txt
  `

  **Commit**: YES (groups with Task 2)
  - Message: refactor(data): creer data/ et deplacer conventions_signees.csv

---

- [ ] 2. Mettre a jour le chemin CSV dans app.py (tabs[6])

  **What to do**:
  - Ligne 2294 : changer le chemin de "conventions_signees.csv" -> "data/conventions_signees.csv"
  - Ajouter creation auto du dossier data/ si inexistant
  - Adapter le message d'erreur si fichier introuvable

  **Must NOT do**:
  - Ne pas modifier le comportement des autres tabs
  - Ne pas changer la logique de lecture/ecriture du CSV

  **Parallelization**:
  - Can Run In Parallel: NO (depends on Task 1)
  - Blocks: Tasks 3, 4
  - Blocked By: Task 1

  **Acceptance Criteria**:
  - [ ] Le chemin lit depuis data/conventions_signees.csv
  - [ ] Si data/ n'existe pas, il est cree automatiquement

  **QA Scenarios**:
  `
  Scenario: Verifier le nouveau chemin
    Tool: Bash (python)
    Steps:
      1. Lire app.py et chercher "conventions_signees.csv"
      2. Verifier que le chemin contient "data"
    Expected Result: Seul "data" apparait dans le chemin
    Evidence: .omo/evidence/task-2-path-update.txt
  `

  **Commit**: YES (groups with Task 1)
  - Message: refactor(app): mettre a jour chemin CSV vers data/

---

- [ ] 3. Remplacer suppression par archivage

  **What to do**:
  - Renommer colonne "Supprimer" en "Archiver"
  - Remplacer le bloc de suppression par un bloc d'archivage
  - Cocher "Archiver" + bouton "Confirmer l'archivage" -> statut passe a "Archive"
  - Ajouter "Archive" dans le selectbox de filtre statut

  **Must NOT do**:
  - Ne pas supprimer les lignes du CSV - seulement changer le statut

  **Parallelization**:
  - Can Run In Parallel: NO (depends on Task 2)
  - Blocked By: Task 2

  **Acceptance Criteria**:
  - [ ] Plus de colonne "Supprimer" - remplacee par "Archiver"
  - [ ] Cocher "Archiver" + bouton -> le statut passe a "Archive"
  - [ ] "Archive" apparait dans le filtre statut

  **QA Scenarios**:
  `
  Scenario: Archiver un projet
    Tool: Bash (python)
    Steps:
      1. Simuler la coche "Archiver" sur un projet
      2. Verifier que le statut passe a "Archive"
      3. Verifier que la ligne existe toujours
    Expected Result: Statut change, ligne preservee
    Evidence: .omo/evidence/task-3-archive.txt
  `

  **Commit**: YES (groups with Task 4)
  - Message: feat(conventions): remplacer suppression par archivage

---

- [ ] 4. Auto-alimentation du formulaire

  **What to do**:
  - Modifier st.date_input("Debut prospection") -> st.date_input("Debut prospection", value=today)
  - today = pd.Timestamp.now() est deja defini, accessible

  **Must NOT do**:
  - Ne pas hardcoder une date

  **Parallelization**:
  - Can Run In Parallel: NO (depends on Task 1)
  - Blocked By: Task 1

  **Acceptance Criteria**:
  - [ ] Le champ "Debut prospection" est pre-rempli avec la date du jour
  - [ ] L'utilisateur peut modifier la date

  **QA Scenarios**:
  `
  Scenario: Verifier la valeur par defaut
    Tool: Bash (grep + python)
    Steps:
      1. grep "date_input" app.py - chercher "value="
      2. Verifier que la variable today est definie
    Expected Result: st.date_input a value=today
    Evidence: .omo/evidence/task-4-auto-date.txt
  `

  **Commit**: YES (groups with Task 3)
  - Message: feat(conventions): auto-alimentation formulaire + filtre Archive

---

## Final Verification Wave

- [ ] F1. Plan Compliance Audit - oracle
- [ ] F2. Smoke Test - syntaxe et coherence tabs[6] - unspecified-high
- [ ] F3. Verification integrite donnees CSV - unspecified-low
- [ ] F4. Scope Fidelity Check - deep

---

## Commit Strategy
- **1-2**: refactor(data): deplacement CSV dans data/ + mise a jour chemins
- **3-4**: feat(conventions): archivage + auto-alimentation formulaire

---

## Success Criteria
- [ ] data/conventions_signees.csv existe avec 5 projets
- [ ] Aucune colonne "Supprimer" dans app.py tabs[6]
- [ ] Colonne "Archiver" + bouton "Confirmer l'archivage" presents
- [ ] "Archive" dans le selectbox filtre statut
- [ ] date_input("Debut prospection") a value=today
- [ ] Les autres tabs (0-5, 7) inches
- [ ] Push deploye sur Streamlit Cloud sans erreur
