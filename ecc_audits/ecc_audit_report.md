# Rapport d'audit ECC — Pilotage B2B (Analyse externe)

Ce rapport a ete genere par un audit externe au dashboard Streamlit.
Aucun fichier du dashboard n'a ete modifie.

## Resume global

- Fichiers audites : 10
- [CRITICAL] : 28
- [HIGH] : 2
- [MEDIUM] : 0
- Total : 30 problemes

**Decision ECC** : BLOCK — corriger les problemes CRITICAL avant toute mise en production

## C:\Users\hachk\pilotage_b2b\app.py

- Lignes : 514
- Taille : 23187 octets
- CRITICAL : 5
- HIGH : 0
- MEDIUM : 0

### CRITICAL (Securite)

- Ligne 327 : Possible api_key hardcode
  - `api_key = ""`
- Ligne 330 : Possible api_key hardcode
  - `k = src.get("LLM_API_KEY", "")`
- Ligne 332 : Possible api_key hardcode
  - `api_key = k`
- Ligne 336 : Possible api_key hardcode
  - `if api_key:`
- Ligne 337 : Possible api_key hardcode
  - `env["LLM_API_KEY"] = api_key`

## C:\Users\hachk\pilotage_b2b\data\transforms.py

- Lignes : 463
- Taille : 19626 octets
- CRITICAL : 5
- HIGH : 0
- MEDIUM : 0

### CRITICAL (Securite)

- Ligne 272 : Possible token hardcode
  - `def _tokens_txt(s) -> set:`
- Ligne 273 : Possible token hardcode
  - `"""Tokens significatifs (≥3 lettres, hors mots vides) pour le match de noms."""`
- Ligne 281 : Possible token hardcode
  - `Match : 1) égalité normalisée du nom  2) ≥ 2 tokens communs (≥3 lettres).`
- Ligne 292 : Possible token hardcode
  - `crm["_tok"] = crm["Nom entreprise"].map(_tokens_txt)`
- Ligne 305 : Possible token hardcode
  - `nt = _tokens_txt(nom)`

## C:\Users\hachk\pilotage_b2b\data\loader.py

- Lignes : 65
- Taille : 2332 octets
- CRITICAL : 0
- HIGH : 0
- MEDIUM : 0

## C:\Users\hachk\pilotage_b2b\metrics\kpi.py

- Lignes : 1008
- Taille : 48010 octets
- CRITICAL : 0
- HIGH : 1
- MEDIUM : 0

### HIGH (Qualite)

- Ligne 1 : Fichier dépasse 800 lignes (1008)
  - `Fichier entier`

## C:\Users\hachk\pilotage_b2b\crm.py

- Lignes : 212
- Taille : 8367 octets
- CRITICAL : 0
- HIGH : 0
- MEDIUM : 0

## C:\Users\hachk\pilotage_b2b\monthly_report.py

- Lignes : 1478
- Taille : 62038 octets
- CRITICAL : 17
- HIGH : 1
- MEDIUM : 0

### CRITICAL (Securite)

- Ligne 17 : Possible api_key hardcode
  - `set LLM_API_KEY=gsk_votre-cle-groq    (dans CMD)`
- Ligne 86 : Possible api_key hardcode
  - `LLM_API_KEY = _GROQ_API_KEY`
- Ligne 90 : Possible api_key hardcode
  - `if LLM_API_KEY:`
- Ligne 325 : Possible api_key hardcode
  - `def call_llm(prompt: str, api_key: str | None = None) -> str | None:`
- Ligne 336 : Possible api_key hardcode
  - `key = api_key or _GROQ_API_KEY`
- Ligne 1138 : Possible api_key hardcode
  - `def _generate_executive_summary(data: dict, api_key: str | None = None) -> dict | None:`
- Ligne 1145 : Possible api_key hardcode
  - `if not api_key and not _OLLAMA_AVAILABLE:`
- Ligne 1212 : Possible api_key hardcode
  - `response = call_llm(prompt, api_key=api_key)`
- Ligne 1281 : Possible api_key hardcode
  - `def analyse(annee: int, mois: int, with_ai: bool = True, with_email: bool = True, api_key: str | None = None):`
- Ligne 1369 : Possible api_key hardcode
  - `response = call_llm(prompt, api_key=api_key)`
- Ligne 1392 : Possible api_key hardcode
  - `if with_ai and api_key:`
- Ligne 1394 : Possible api_key hardcode
  - `exec_summary = _generate_executive_summary(data, api_key=api_key)`
- Ligne 1451 : Possible api_key hardcode
  - `parser.add_argument("--api-key", type=str, default=None,`
- Ligne 1452 : Possible api_key hardcode
  - `help="Cle API LLM (alternative a LLM_API_KEY env)")`
- Ligne 1474 : Possible api_key hardcode
  - `api_key=args.api_key or _GROQ_API_KEY)`
- Ligne 1107 : Possible password hardcode
  - `server.login(EMAIL_FROM, EMAIL_PASSWORD)`
- Ligne 349 : Possible token hardcode
  - `"max_tokens": 8000,`

### HIGH (Qualite)

- Ligne 1 : Fichier dépasse 800 lignes (1478)
  - `Fichier entier`

## C:\Users\hachk\pilotage_b2b\monthly_report_v2.py

- Lignes : 451
- Taille : 21099 octets
- CRITICAL : 0
- HIGH : 0
- MEDIUM : 0

## C:\Users\hachk\pilotage_b2b\send_report.py

- Lignes : 390
- Taille : 19284 octets
- CRITICAL : 1
- HIGH : 0
- MEDIUM : 0

### CRITICAL (Securite)

- Ligne 68 : Possible password hardcode
  - `server.login(EMAIL_FROM, EMAIL_PASSWORD)`

## C:\Users\hachk\pilotage_b2b\trend_analyzer.py

- Lignes : 410
- Taille : 18367 octets
- CRITICAL : 0
- HIGH : 0
- MEDIUM : 0

## C:\Users\hachk\pilotage_b2b\trend_alert_panel.py

- Lignes : 449
- Taille : 17681 octets
- CRITICAL : 0
- HIGH : 0
- MEDIUM : 0

## Checklist ECC appliquée

- **CRITICAL (Securite)** : points de controle verifies
- **HIGH (Qualite)** : points de controle verifies
- **MEDIUM (Bonnes pratiques)** : points de controle verifies

---
*Rapport genere par ecc_audit_project.py. Audit externe — le dashboard Streamlit est intact.*