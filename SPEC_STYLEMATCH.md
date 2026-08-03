# STYLEMATCH AI - Spécification Complète

## Application Mobile de Styling Masculin avec IA

**Version:** 1.0  
**Date:** Avril 2026  
**Status:** Brief de conception validé

---

## 1. Résumé Exécutif

**STYLEMATCH AI** est une application mobile de styling masculine alimentée par l'IA qui permet aux hommes de digitizer leur garde-robe et de recevoir des recommandations de tenues personnalisées basées sur leur wardrobe réel, la météo, le calendrier et les occasions.

### Problème résolu
La majorité des hommes passent trop de temps chaque matin à decidir quoi porter. Ils ont des vêtements dans leur garde-robe mais ne savent pas les coordonner efficacement.

### Proposition de valeur
- Digitization automatique de la garde-robe via photo
- Recommandations quotidiennes intelligentes en 10 secondes
- Apprentissage du style personnel pour des suggestions de plus en plus pertinentes
- Intégration météo et calendrier pour des décisions.contextuelles

---

## 2. Analyse du Marché

### 2.1 Paysage concurrentiel

| App | Force principale | Faiblesse | Prix |
|-----|--------------|----------|------|
| **Styled (USA)** | Intégration calendrier+météo, UX rapide | Payant, limité aux US, pas de virtual try-on | €9.99/mois |
| **Vaiko (Europe)** | Shopping intégré, dual-agent | Complexe, trop de features | €9-67/mois |
| **GAUGE (USA)** | Analyse de style professionnelle | En cours de développement iOS, interface chargée | €14.99/mois |
| **SELION.AI** | Gratuit, open-source | Pas de virtual try-on, IA basique | Gratuit |
| **Acloset** | Setup rapide | Pas d'IA conversationnelle, suggestions limitées | Gratuit |

### 2.2 Opportunités identifiées

1. **Marché francophone sous-exploité** - Pas d'app majeure dédiée aux hommes français/européens
2. **Virtual Try-On différenciant** - Few apps le proposent bien (Vinchy, Pocket Stylist)
3. **UX épurée** - Les apps existantes sont complexes, marge pour simplifier
4. **IA conversationnelle** - majorités utilisent des rules-based systems, pas de vrai对话
5. **Intégration shopping douce** - Pas d'app qui propose achats sans pushes agressifs

### 2.3 Cible utilisateur

- **Primaire:** Hommes 25-45 ans, urbains, soucieux de leur apparence
- **Secondaire:** Hommes 18-25 ans qui veulent développer leur style
- **Tertiaire:** Hommes 45+ qui veulent moderniser leur wardrobe

**Profile type:** Utilisateur busy qui optimise sa vie (travail, fitness, productivité) mais struggle avec le style quotidien. Il a les vêtements mais pas le temps de les التفكير.

---

## 3. Spécification fonctionnelle

### 3.1 Fonctionnalités Core

#### F1: Digitization de Garde-Robe
- **Description:** Photographier chaque vetement et l'IA identifie automatiquement catégorie, couleur, matière, niveau de formalité
- **Input:** Photo (camera ou galerie) par item
- **Output:** Fiche item cataloguée avec tags IA + possibilités de correction manuelle
- **Categories supportées:**
  - Tops (t-shirts, chemises, polos, pulls, vestes, manteaux)
  - Bottoms (jeans, pantalons, shorts)
  - Shoes (baskets, boots, mocassins, sandales)
  - Accessories (ceintures, sacs, montre, chapeau, earrings)
- **Attributes IA:**
  - Catégorie principale + sous-catégorie
  - Couleur(s) principale(s)
  - Motif (uni, rayures, carreaux, imprimés)
  - Matière (coton, laine, linen, synthétique, cuir)
  - Formalité (casual, smart casual, business, formal)
  - Saison (printemps, été, automate, hiver, all-season)

#### F2: Recommandations de Tenues
- **Description:** L'IA génère des tenues complètes basées sur éléments disponibles
- **Inputs:**
  - Occasion sélectionnée (quotidien, travail, date, événement spéciale)
  - Météo du jour (API externe)
  - Événements日历 (optionnel)
  - Préférences utilisateur (via historique de feedback)
- **Output:**
  - 3-5 tenues suggérées avec visualisation
  - Score de style (1-10) avec explication
  - Breaking news: chaque piece recommandée et pourquoi
- **Règles IA:**
  - Harmonie des couleurs
  - Formal compatibilité (pas de sneakers avec costume)
  - Layering approprié selon saison/météo
  - Pas de repetition immédiate (suivi du wardrobe usage)

#### F3: Assistant IA Conversationnel
- **Description:** Dialogue en langage naturel avec l'IA stylist
- **Capacités:**
  - "Quoi porter pour un entretien d'embauche?"
  - "Je veux un look plus mature pour un diner"
  - "Suggest quelque chose de différent aujourd'hui"
  - "Complète ma tenue avec des accessoires"
- **Features:**
  - Conversation persistante (mémoire du style)
  - Suggestion shopping si wardrobe manquante
  - Feedback interactif (accept/refuse/correction)

#### F4: Planification de Tenues
- **Description:** Planifier les tenues pour la semaine/semaine à venir
- **Features:**
  - Vue calendrier 7 jours
  - Drag & drop pour assigner tenues
  - Météo forecast affichée
  - Rappel notification Jour J

#### F5: Virtual Try-On (v2)
- **Description:** Visualiser comment une tenue looks sur soi
- **Note:** Feature v2 (post-MVP) - nécessite infrastructure AI additionnelle

### 3.2 Fonctionnalités Secondaires

#### F6: Style Analytics
- **Stats affichées:**
  - Wardrobe utilization (pièces portées vs non-portées)
  - Most worn items
  - Color palette dominante
  - Gaps identifiés (pieces manquantes)
  - Cost-per-wear tracker

#### F7: Shopping Advisor
- **Description:** Suggestions de pièces à ajouter basées sur gaps identifiés
- **Output:** Links vers e-commerces partenaires (affiliate)

#### F8: Social Sharing
- **Description:** Partager outfits sur Instagram/Stories
- **Output:** Image formatée avec branding

### 3.3 User Flows

```
[Onboarding]
    ↓
[Photo premier vetement] → [IA categorize] → [Confirmer/corriger]
    ↓
[Ajouter 10-20 pieces] (processus guidé)
    ↓
[Style quiz rapide] (options, occasions fréquentes)
    ↓
[Home screen: Today's recommendation]
```

```
[Daily Usage]
    ↓
[Ouvrir app] → [Voir recommandation du jour]
    ↓
[Accepter ✓] ou [Refuser ✗] ou [Voir autres options]
    ↓ 
[L'IA apprend du feedback]
```

```
[Style Advisor]
    ↓
[Ouvrir chat] → [Taper question]
    ↓
[IA répond avec suggestion + explanation]
    ↓
[Accepter → Ajouter à wardrobe] ou [Demander autre]
```

### 3.4 States & Edge Cases

| State | Condition | User Feedback |
|-------|----------|------------|
| Empty | 0 pièces | "Commencez par ajouter vos essentiels" + Quick-add guide |
| Sparse | 1-9 pièces | "Ajoutez plus de pièces pour de meilleures idées" |
| Loading | Upload photo | Skeleton + "Analyse en cours..." |
| Error API | Échec détection | "Réessayez ou saisissez manuellement" |
| No match | Pas de tenue pour critères | "Essayez d'ajouter plus de variety" |
| Offline | Pas de connexion | Mode dégradé avec suggestions cached |

---

## 4. Spécification Technique

### 4.1 Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    React Native (Expo)                  │
├─────────────────────────────────────────────────────────┤
│  UI Layer: React Navigation, NativeWind (Tailwind)      │
│  State: Zustand / React Context                        │
│  Storage: AsyncStorage + SQLite                       │
└─────���─��────────────────┬────────────────────────────────┘
                     │ REST APi
                     ▼
┌─────────────────────────────────────────────────────────┐
│                   Backend (Node.js/FastAPI)            │
├─────────────────────────────────────────────────────────┤
│  API Gateway                                        │
│  ├── Wardrobe Service                               │
│  ├── Outfit Engine (LLM + Rules)                 │
│  ├── Weather API (OpenWeatherMap)                  │
│  └── Calendar Service (caldav/Google)             │
├─────────────────────────────────────────────────────────┤
│  Database: PostgreSQL (Supabase)                     │
│  Object Storage: S3/R2                              │
│  Cache: Redis                                     │
└─────────────────────────────────────────────────────────┘
```

### 4.2 Tech Stack

| Layer | Technology | Justification |
|-------|------------|-------------|
| **Frontend** | React Native + Expo 54 | Vitesse dev, cross-platform iOS/Android, expo-router |
| **Styling** | NativeWind (Tailwind) | Design system cohérent, responsive |
| **State** | Zustand | Simple, performant, persisted |
| **Storage** | AsyncStorage + expo-sqlite | Local-first, offline capable |
| **Backend** | FastAPI (Python) ou Node.js | LLM integration native |
| **DB** | Supabase (PostgreSQL) | Auth, database, storage, realtime |
| **AI Vision** | Google Gemini 2.0 Flash | Detection vetements, analysis |
| **LLM** | Claude 3.5 Sonnet ou Gemini 2.0 | Conversation, recommandations |
| **Weather** | OpenWeatherMap API | Données météo |
| **Auth** | Supabase Auth | Email, Google, Apple sign-in |

### 4.3 API Integration

#### Clothing Detection (Gemini Vision)
```python
# Input: image base64
# Prompt: "Identify this clothing item with category, color, pattern, material, formality level"
# Output: JSON structuré
{
  "category": "shirt",
  "category_confidence": 0.92,
  "colors": [{"name": "navy", "percentage": 70}, {"name": "white", "percentage": 30}],
  "pattern": "uni",
  "material": "coton",
  "formality": "smart_casual",
  "season": ["spring", "fall"]
}
```

#### Outfit Generation (LLM)
```python
# Input: wardrobe_items + occasion + weather + user_preferences
# Output: structured outfit recommendation
{
  "outfit": [
    {"item_id": "abc123", "slot": "top", "layering_position": 1},
    {"item_id": "def456", "slot": "bottom", "layering_position": 2},
    {"item_id": "ghi789", "slot": "shoes", "layering_position": 3}
  ],
  "style_score": 8.5,
  "reasoning": "Couleurs harmonieuses, niveau de formalité cohérent..."
}
```

### 4.4 Data Models

```
User
├── id: UUID
├── email: string
├── preferences: JSON (style, occasions)
├── created_at: timestamp
└── style_profile: JSON

ClothingItem
├── id: UUID
├── user_id: UUID
├── image_url: string
├── category: string
├── subcategory: string
├── colors: string[]
├── pattern: string
├── material: string
├── formality: enum
├── season: string[]
├── times_worn: int
├── last_worn: timestamp
├── is_active: boolean
└── created_at: timestamp

Outfit
├── id: UUID
├── user_id: UUID
├── items: UUID[] (ordered)
├── occasion: string
├── weather: string
├── rating: int (optional)
├── feedback: string (optional)
├── created_at: timestamp
└── is_repeated: boolean

Conversation
├── id: UUID
├── user_id: UUID
├── messages: Message[]
├── created_at: timestamp
└── updated_at: timestamp
```

---

## 5. Design System

### 5.1 Direction Esthétique

**Direction:** Premium Minimal - Charismatique mais accessible

Pas de cyberpunk ou neon. Pas de gradients compliqués. Un design qui inspire confiance et sophistication. Le type d'interface qu'un directeur technique ou médecin utiliserait.

### 5.2 Couleurs

| Rôle | Couleur | Usage |
|------|--------|-------|
| **Background** | #0A0A0B | Dark primary (OLED-friendly) |
| **Surface** | #16161A | Cards, elevated surfaces |
| **Surface Alt** | #1E1E24 | Secondary surfaces |
| **Primary** | #C9A962 | Or rose - luxe discret |
| **Primary Hover** | #D4B872 | Primary state |
| **Accent** | #E8E8E8 | Text principal |
| **Muted** | #8A8A8F | Descriptions, labels |
| **Success** | #4ADE80 | Confirmations |
| **Error** | #F87171 | Erreurs |

### 5.3 Typographie

| Usage | Font | Weight | Size |
|-------|------|--------|-----|
| **Display** | Syne | 700 | 32-48px |
| **Heading** | Syne | 600 | 24-28px |
| **Body** | Manrope | 400-500 | 16px |
| **Caption** | Manrope | 400 | 14px |
| **Label** | Manrope | 500 | 12px (uppercase) |

### 5.4 Layout & Spacing

- **Base:** 4px grid (4, 8, 12, 16, 24, 32, 48)
- **Radius:** 12px (cards), 8px (buttons), 24px (pills)
- **Spacing:** Generous - chaque section a de l'air
- **Max-width contenu:** 65ch pour lisibilité optimale

### 5.5 Composants Clés

#### Cards (Clothing/Outfit)
- Image principale (aspect-ratio 3:4)
- Tags en bas (catégorie, couleur)  
- Petit indicator de formality (dot colored)

#### Buttons
- Primary: Fond Primary, texte dark (inverted)
- Secondary: Transparent, bord Primary
- Ghost: Texte only avec hover state

#### Chat Interface
- Bubble style (user right, AI left)
- Typing indicator: 3 dots animated
- Context cards: mini previews

### 5.6 Animations

- **Entrance:** Fade + slide up (200ms, ease-out-quart)
- **Transitions:** Subtle crossfade (150ms)
- **Haptics:** Light impact sur selections
- **Loading:** Minimal skeleton, pas de spinner fancy

---

## 6. Modèle Économique

### 6.1 Freemium

| Feature | Free | Premium |
|---------|------|--------|
| Digitization wardrobe | 20 pièces | Illimité |
| Recommandations/jour | 3 | Illimité |
| Chat IA | Limit/day | Illimité |
| Analytics | Basic | Complete |
| Calendar planning | 3 jours | 7 jours |
| Virtual Try-On | - | ✓ |
| Export/Share | - | ✓ |
| **Prix** | **€0** | **€6.99/mois** |

### 6.2 Revenus additionnels

1. **Affiliate shopping** - Commission sur pieces recommandées vendues (10-20%)
2. **Sponsored slots** - Marques partenaires dans suggestions (optionnel, carefully curated)
3. **B2B licensing** - API pour retailers/marques

### 6.3 Critères de succès

- **Taux de conversion:** 5% free → premium (benchmark: 3-8%)
- **DAU/MAU:** 30% (benchmark: 20-40%)
- **Day 7 retention:** 40%
- **Wardrobe avg:** 35 pièces par utilisateur actif

---

## 7. Phases de Développement

### Phase 1: MVP (8-10 semaines)
- [ ] Setup projet React Native + Expo
- [ ] Auth + onboarding
- [ ] Camera + upload clothing
- [ ] AI detection (Gemini)
- [ ] Wardrobe view (CRUD)
- [ ] Basic recommendation engine
- [ ] Home screen + today's outfit

### Phase 2: AI Enhancement (4-6 semaines)
- [ ] Conversational AI (LLM)
- [ ] Feedback learning
- [ ] Style analytics
- [ ] Weather integration
- [ ] Push notifications

### Phase 3: Scale (4-6 semaines)
- [ ] Calendar integration
- [ ] Social sharing
- [ ] Virtual Try-On (v2)
- [ ] Shopping features
- [ ] Performance optimization

---

## 8. Risques & Mitigations

| Risk | Probability | Impact | Mitigation |
|------|------------|-------|-----------|
| AI detection inaccurate | HIGH | MEDIUM | Fallback manuel, feedback loop |
| LLM costs too high | MEDIUM | HIGH | Caching, prompt optimization |
| User dropout during onboarding | HIGH | HIGH | Friction réduite, gamification |
| Competition moved in | MEDIUM | MEDIUM | Fast follow, unique features |
| API rate limits | MEDIUM | MEDIUM | Multi-provider fallback |

---

## 9. Prochaines Étapes

1. **Valider le brief** - Confirmer les spécifications avec les parties prenantes
2. **Setup environnement** - Repo Git + Expo project initialisé
3. **Prototype UI** - Créer les screens principaux (Figma style)
4. **User testing** - Tests utilisateurs sur mockups
5. **Backend MVP** - API clothing detection + outfit generation
6. **Integration** - Connecter le tout
7. **Beta** - Lancer avec 50 users

---

## Annexe: References

### Apps analysées
- Styled (getstyled.app)
- Vaiko (vaiko.store)
- GAUGE (gaugestyle.app)
- DRESSED (trydressed.com)
- SELION.AI (selionai.app)
- Vaiko (vaiko.store)
- Vinchy (vinchy.app)
- Pocket Stylist (pocketstylist.app)

### Technologies
- Google Gemini Vision API
- Claude (Anthropic)
- React Native + Expo
- Supabase
- OpenWeatherMap API

### Design refs
- Syne + Manrope typography pairing
- Dark mode premium avec touches or rose
- Spacing généreux, hierarchie claire