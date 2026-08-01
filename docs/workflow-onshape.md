# Workflow Onshape — Options d'automatisation

## Contexte

Ce projet vise à automatiser la conception d'un bateau à voile dans Onshape via FeatureScript. Le workflow idéal est :

```
Variables paramétriques → FeatureScript → Feature Studio → Part Studio → Géométrie 3D
```

Trois approches ont été explorées pour automatiser l'injection de FeatureScript dans Onshape.

---

## Option 1 : Semi-automatique (Recommandée pour démarrer)

### Principe

L'humain crée la structure (Feature Studios, Part Studios) manuellement dans Onshape. L'agent injecte le code FeatureScript dans les Feature Studios existants via Playwright.

### Workflow

```
1. Humain crée "Boat Variables.fs" dans Onshape
2. Humain crée "Hull Feature.fs" dans Onshape
3. Humain crée "Boat Assembly" Part Studio dans Onshape
4. @cad génère le code FeatureScript
5. Script Playwright injecte le code dans les Feature Studios
6. Humain clique "Commit" dans chaque Feature Studio
7. Le Part Studio se régénère automatiquement
```

### Avantages

- ✅ **Fiable** — pas de dépendance aux sélecteurs UI fragiles
- ✅ **Contrôle humain** sur la structure du document
- ✅ **Rapide à mettre en place** — pas de configuration API
- ✅ **Debug facile** — l'humain voit ce qui se passe

### Inconvénients

- ❌ Création manuelle des tabs (une fois seulement)
- ❌ Commit manuel (un clic par Feature Studio)
- ❌ Pas 100% automatisé

### Scripts associés

- `scripts/inject_featurescript_v2.py` — injection dans Feature Studio existant
- `scripts/commit_featurescript.py` — (à créer) commit automatique

### Cas d'usage

Idéal pour un projet personnel avec un nombre limité de Feature Studios (5-10).

---

## Option 2 : API REST Onshape (Recommandée pour production)

### Principe

Utiliser l'[API REST officielle d'Onshape](https://onshape-public.github.io/docs/) pour créer Feature Studios, Part Studios, et injecter du code programmatiquement.

### Workflow

```
1. Créer une app Onshape (developer portal)
2. Obtenir access_key, secret_key, API key
3. Script Python utilise l'API pour :
   a. Créer Feature Studio "Boat Variables"
   b. Injecter les variables (LOA, Beam, Draft...)
   c. Créer Feature Studio "Hull Feature"
   d. Injecter le code de la feature Hull
   e. Commit chaque Feature Studio via API
   f. Créer Part Studio "Boat Assembly"
   g. Instancier les features dans le Part Studio
```

### Avantages

- ✅ **100% automatisé** — de l'idée à la géométrie
- ✅ **Robuste** — pas de sélecteurs CSS fragiles
- ✅ **Versionnable** — les appels API sont déterministes
- ✅ **CI/CD possible** — génération automatique à chaque commit
- ✅ **Multi-documents** — gestion de plusieurs versions du bateau

### Inconvénients

- ❌ Nécessite une app Onshape (developer account)
- ❌ Configuration OAuth2 (access_key, secret_key)
- ❌ Courbe d'apprentissage de l'API
- ❌ Rate limits (1000 requêtes/heure pour free tier)

### Endpoints clés

| Endpoint | Usage |
|----------|-------|
| `POST /api/documents/{did}/elements` | Créer un élément (Feature Studio, Part Studio) |
| `PUT /api/documents/{did}/elements/{eid}/contents` | Injecter du FeatureScript |
| `POST /api/elements/{eid}/commit` | Commit un Feature Studio |
| `POST /api/parts/{did}/{wid}/{eid}/features/feature-script` | Exécuter FeatureScript dans Part Studio |

### Scripts associés

- `scripts/onshape_api_client.py` — (à créer) wrapper API
- `scripts/create_boat.py` — (à créer) orchestration complète

### Cas d'usage

Idéal pour un projet collaboratif, CI/CD, ou génération paramétrique à grande échelle.

### Configuration requise

```bash
# 1. Créer une app sur https://dev-portal.onshape.com
# 2. Obtenir les credentials
export ONSHAPE_ACCESS_KEY="your_access_key"
export ONSHAPE_SECRET_KEY="your_secret_key"
export ONSHAPE_API_KEY="your_api_key"

# 3. Installer les dépendances
pip install requests requests-oauthlib
```

---

## Option 3 : Template FeatureScript monolithique

### Principe

Un seul Feature Studio contient tout le code du bateau. Un seul Part Studio l'utilise. Pas de modularité, mais simplicité maximale.

### Workflow

```
1. Humain crée "Boat.fs" Feature Studio
2. Humain crée "Boat" Part Studio
3. @cad génère un FeatureScript monolithique
4. Script injecte tout le code dans "Boat.fs"
5. Humain commit
6. Le Part Studio affiche tout le bateau
```

### Structure du FeatureScript

```featurescript
FeatureScript 2384;
import(path : "onshape/std/geometry.fs", version : "2384.0");

// === VARIABLES ===
const LOA = 4000 * millimeter;
const BEAM = 1500 * millimeter;
const DRAFT = 300 * millimeter;
const HULL_THICKNESS = 2 * millimeter;

// === FEATURES ===
annotation { "Feature Type Name" : "Hull" }
export const hull = defineFeature(function(context is Context, id is Id, definition is map)
    precondition { ... }
    { ... });

annotation { "Feature Type Name" : "Deck" }
export const deck = defineFeature(function(context is Context, id is Id, definition is map)
    precondition { ... }
    { ... });

annotation { "Feature Type Name" : "Keel" }
export const keel = defineFeature(function(context is Context, id is Id, definition is map)
    precondition { ... }
    { ... });
```

### Avantages

- ✅ **Simple** — un seul fichier à gérer
- ✅ **Variables centralisées** — toutes au même endroit
- ✅ **Pas de dépendances** entre Feature Studios

### Inconvénients

- ❌ **Fichier unique** — devient ingérable au-delà de ~500 lignes
- ❌ **Pas de réutilisation** — les features ne sont pas partageables
- ❌ **Regénération complète** — chaque modif régénère tout le bateau
- ❌ **Pas de collaboration** — difficile de travailler à plusieurs

### Cas d'usage

Prototypes rapides, bateaux simples (< 10 features), POC.

---

## Recommandation

| Phase | Option | Pourquoi |
|-------|--------|----------|
| **Maintenant** | Option 1 (Semi-auto) | Démarrer vite, valider le workflow |
| **Court terme** | Option 3 (Template) | Si le bateau reste simple |
| **Long terme** | Option 2 (API REST) | Pour un projet collaboratif/CI-CD |

### Plan d'action

1. **Semaine 1** : Option 1 — créer manuellement les Feature Studios, automatiser l'injection
2. **Semaine 2-3** : Option 3 — consolider en un template si le bateau reste simple
3. **Mois 2+** : Option 2 — migrer vers l'API REST si le projet grossit

---

## Ressources

- [FeatureScript Documentation](https://cad.onshape.com/FsDoc/)
- [Onshape API Reference](https://onshape-public.github.io/docs/)
- [Onshape Developer Portal](https://dev-portal.onshape.com/)
- [FeatureScript Standard Library](https://cad.onshape.com/FsDoc/library.html)
