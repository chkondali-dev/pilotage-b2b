# Rapport Mensuel IA — Design Specification

**Statut** : ✅ **IMPLÉMENTÉ** — `monthly_report.py` en production (KPIs → LLM Groq → HTML → email).
Ce document reste la référence du format et du pipeline.

## Vue d'ensemble

**Projet :** Pilotage B2B — SMG (MG & BATAM)
**Objectif :** Automatiser la génération du rapport mensuel conventions + EDC avec analyse IA par convention, commentaires intelligents, et recommandations actionnables
**Livrable :** Script Python `monthly_report.py` + prompt template IA
**Base :** Données Excel GitHub, pipeline email existant (`send_report.py`), KPI engine (`app.py`)

---

## Architecture

### Fichiers

```
pilotage_b2b/
├── monthly_report.py      ← NOUVEAU : Orchestrateur du rapport mensuel
│                            (chargement données → KPIs → analyse IA → HTML → email)
├── prompts/
│   └── analyse_convention.md  ← NOUVEAU : Prompt template pour analyse IA
├── send_report.py         ← EXISTANT (inchangé — référencé pour réutilisation)
├── app.py                 ← EXISTANT (inchangé — KPI engine réutilisé)
└── 2025/                  ← EXISTANT (données Excel)
```

### Pipeline

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Données     │ ──→ │  Calcul      │ ──→ │  Analyse     │ ──→ │  Envoi       │
│  Excel       │     │  KPIs        │     │  IA          │     │  Email       │
│  (GitHub)    │     │  mensuels    │     │  (LLM)       │     │  (SMTP SMG)  │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
       │                    │                    │                    │
       │ load_all_data()    │ ca_sum()           │ prompt structuré   │ send_email()
       │ depuis send_report │ evol_pct()          │ + JSON output      │ depuis send_report
       │                    │ convention_risk    │                    │
       │                    │ inactive_conv()    │                    │
       └────────────────────┴────────────────────┴────────────────────┘
                    Réutilisation du code existant (app.py)
```

---

## Format du rapport mensuel

Le rapport conserve la structure actuelle (validée par l'utilisateur) avec enrichissement IA :

### 1. PERFORMANCE GLOBALE — SYNTHÈSE

| Indicateur | N | N-1 | Variation |
|---|---|---|---|
| CA TTC conventions | 1 121 322 TND | 1 503 371 TND | -25,40% |
| CA TTC EDC | 65 486 TND | 3 752 TND | +1645% |
| CA TOTAL COMBINÉ | 1 186 808 TND | 1 507 123 TND | -21,30% |
| Nombre de dossiers | 592 | 789 | -25,00% |
| ... | ... | ... | ... |

**Commentaire IA :** Généré automatiquement, met en contexte les chiffres bruts.

### 2. ANALYSE PAR CONVENTION

Chaque convention reçoit un diagnostic structuré :

```
┌─────────────────────────────────────────────────────────────┐
│ 🏥 Amicale Ben Arous                             🟢 Croissance │
│ CA: 45 200 TND | Évolution: +12% vs N-1 │ Risque: Faible   │
│                                                             │
│ Commentaire IA : "Performance solide et constante.          │
│ 87 adhérents actifs, taux d'impayés à 2.3%.                 │
│ Tendence haussière depuis 3 mois confirmée."                │
│                                                             │
│ Recommandation : ✅ RECONDUIRE                              │
│ Action : Proposer extension plafond de 3000→4000 DT          │
└─────────────────────────────────────────────────────────────┘
```

**Signaux :**
- 🟢 **Croissance** — CA en hausse significative
- 🟡 **Stable / À surveiller** — CA quasi stable ou légère baisse
- 🔴 **Alerte** — Baisse forte et/ou continue
- ⚫ **Inactif** — Aucune facture depuis N jours

### 3. ANALYSE PAR MAGASIN

Tables existantes : Top contributeurs, progressions notables, magasins en baisse.

L'IA génère les commentaires par magasin et les priorités d'action.

### 4. CONVENTION EDC — ÉDUCATION NATIONALE

Section dédiée avec KPIs spécifiques à EDC.

### 5. CONCLUSION + PRIORITÉS (généré par IA)

Synthèse exécutive + plan d'action priorisé par l'IA.

---

## Analyse IA — Détail technique

### Prompt LLM (via API)

À chaque exécution mensuelle, le script construit un prompt structuré contenant :

1. **Données globales du mois** (tableau synoptique)
2. **Données par convention** (CA N, CA N-1, évolution, type garantie, nb adhérents, impayés)
3. **Données par magasin** (CA, évolution)
4. **Données EDC**

Le prompt demande à l'IA de retourner un **JSON structuré** :

```json
{
  "synthese_globale": "Texte de synthèse...",
  "conventions": [
    {
      "nom": "Amicale Ben Arous",
      "signal": "green",
      "risque": "faible",
      "tendance": "croissance_constante",
      "commentaire": "...",
      "recommandation": "reconduire",
      "action": "..."
    }
  ],
  "priorites": [
    "1. Lancer renouvellement Amicale Ben Arous",
    "2. Visite terrain COFICAB TUNIS"
  ],
  "conclusion": "Texte de conclusion..."
}
```

### Fournisseur IA

- **API OpenAI** (GPT-4o-mini) ou **API Claude** (recommandé)
- Coût estimé : ~0.10-0.30€ par rapport mensuel
- Clé API configurée via variable d'environnement (`.env`)
- Fallback : si API indisponible, rapport généré sans commentaires IA

### Découpage IA (optionnel pour rapports longs)

Si >30 conventions, découpage en lots de 15 conventions par appel API pour éviter les limites de contexte.

---

## Spécifications fonctionnelles

### Entrées
- Fichiers Excel chargés depuis GitHub (identique à `send_report.py`)
- Mois/année cible (défaut : mois précédent)

### Sorties
- Email HTML envoyé via SMTP SMG
- Copie locale du rapport (HTML)

### Configuration

```python
# Config (dans le script ou .env)
MONTHLY_RECIPIENTS = [
    "Hamadi.Chkondali@SMG.com.tn",
    # ... autres destinataires
]
SMTP_SERVER = "mail.SMG.com.tn"
SMTP_PORT = 587
LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_MODEL = "gpt-4o-mini"  # ou "claude-3-haiku"
```

### Gestion d'erreurs

| Erreur | Comportement |
|---|---|
| Fichier Excel non trouvé | Skip ce fichier, continue avec les autres |
| API IA indisponible | Rapport sans commentaires IA (mode dégradé) |
| SMTP indisponible | Sauvegarde locale uniquement |
| Données insuffisantes | Rapport avec message explicatif |

### Planification

- **Windows Task Scheduler** : exécution le 1er de chaque mois à 8h00
- Alternative : déclenchement manuel via `python monthly_report.py`

---

## Réutilisation du code existant

### Depuis `send_report.py`
- `load_excel(url)` → chargement fichiers
- `send_email(subject, html_body)` → envoi SMTP
- `format_k(x)` → formatage nombres
- Constantes : `EMAIL_FROM`, `SMTP_SERVER`, `SMTP_PORT`, `FILES`

### Depuis `app.py`
- `ca_sum(df, annee, mois)` → CA par période
- `evol_pct(n, n1)` → pourcentage d'évolution
- `convention_risk_matrix(df_vc, annee_n)` → matrice risque
- `inactive_conventions(df_vc, threshold_days)` → conventions inactives
- `_add_date_cols(df)` → parsing dates
- `_map_magasins(df, code_df)` → mapping codes magasins

Les fonctions sont importées directement (pas de duplication) via restructuration en module utilitaire, OU copiées dans `monthly_report.py` si l'isolation est préférée.

**Décision :** Copier les fonctions nécessaires dans `monthly_report.py` pour garder le script autonome (pas de dépendance à `app.py` qui est un dashboard Streamlit). Le KPI engine sera extrait dans une section dédiée.

---

## Format email

**Objet :** `Rapport Mensuel Pilotage Conventions — {Mois} {Année}`

**Structure HTML :**
- En-tête MG/BATAM avec mois
- Section KPI globaux (tableau comparatif)
- Section Top Performers (tableau + commentaires IA)
- Section Alertes / Comptes en baisse (tableau + commentaires IA + actions)
- Section Magasins (top, progressions, baisses)
- Section EDC
- Conclusion + Priorités (IA)
- Pied de page SMG

**Destinataires :** Configurable (défaut : Hamadi + direction commerciale)

---

## Tests et validation

1. **Test unitaire** : exécution du script avec données du mois précédent
2. **Validation manuelle** : lecture du rapport HTML généré
3. **Test email** : vérification de l'envoi et du rendu
4. **Comparaison** : les chiffres du rapport automatisé doivent correspondre aux chiffres du rapport manuel du même mois

---

## Prochaines étapes

1. ✅ Design validé
2. 🔲 Implémentation `monthly_report.py`
3. 🔲 Rédaction prompt IA (`prompts/analyse_convention.md`)
4. 🔲 Test avec données réelles du mois précédent
5. 🔲 Configuration planification automatique
6. 🔲 Livraison finale
