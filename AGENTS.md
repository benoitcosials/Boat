# Boat — Conventions & Architecture du Projet

## Structure des Répertoires

```
Boat/
├── math/                     # Modules JAX — calculs sur GPU Metal
│   ├── hull_surface.py       # Surface de coque (Bézier 4×4)
│   └── hydrostatics.py       # Hydrostatique (volume, LCB, Cb, Cp, Cm)
│
├── parts/                    # Définitions persistantes des pièces (FeatureScript)
│   ├── *.fs                  # Fichiers FeatureScript — le "blueprint" versionné
│   │                         # Lisibles par le LLM et l'humain, réutilisables
│
├── scripts/                  # Scripts utilitaires projet (à venir : wrappers JAX)
│
├── tests/                    # Tests et fixtures QA
│   └── fixtures/             # JSON de test pour les gates 1-2
│       ├── valid_spec.json
│       ├── bad_spec.json
│       ├── valid_params.json
│       └── bad_params.json
│
├── tmp/                      # Fichiers temporaires, brouillons, rapports
│
├── .opencode/
│   ├── agents/
│   │   └── cad.agent.md      # Agent principal — orchestrateur 5 phases
│   ├── skills/
│   │   ├── cad-requirements/ # Phase 1 : Interview → spec.json
│   │   ├── cad-naval-math/   # Phase 2 : JAX → params.json
│   │   ├── cad-featurescript-gen/ # Phase 3 : FeatureScript Onshape
│   │   ├── cad-onshape-injector/ # Phase 4 : Playwright → Onshape
│   │   └── cad-qa/           # Phase 5 : Validation STL + printabilité
│   └── archive/              # Ancien pipeline FreeCAD (historique)
│
├── .env                      # Credentials Onshape (gitignoré)
├── .env.example              # Template pour .env
├── .envrc                    # direnv : active venv + charge .env
├── .gitignore                # .env, .venv/, .browser-data/, __pycache__
├── .venv/                    # Python 3.12 isolé (gitignoré)
├── requirements.txt          # jax, jax-metal, playwright, trimesh
└── README.md                 # Setup & dépendances
```

## Usage des Répertoires

| Répertoire | Usage | Modifiable par |
|-----------|-------|---------------|
| `math/` | Modules JAX de calcul naval | L'agent via `cad-naval-math` |
| `parts/` | Définitions FeatureScript des pièces | `cad-featurescript-gen` écrit, `cad-onshape-injector` lit, humain édite |
| `scripts/` | Scripts utilitaires wrappers | L'agent via `cad-naval-math` |
| `tests/fixtures/` | Données de test pour QA gates | Les scripts `cad-qa/scripts/` |
| `tmp/` | Fichiers temporaires uniquement | Tout le monde — pas de code stable ici |
| `.opencode/` | Artéfacts AI (agents, skills) | L'agent `forge` uniquement |
| `.opencode/archive/` | Anciennes versions pour référence | Lecture seule |

## Inventaire des Agents & Skills

### Agent

| Agent | Modèle | Rôle |
|-------|--------|------|
| `cad` | `opencode-go/deepseek-v4-pro` | Orchestrateur naval/CAO : idée → fabrication |

### Skills

| Skill | Phase | Entrée | Sortie | Outils |
|-------|-------|--------|--------|--------|
| `cad-requirements` | 1 | Description utilisateur | `spec.json` | Interview structurée |
| `cad-naval-math` | 2 | `spec.json` | `params.json` | JAX Metal GPU |
| `cad-featurescript-gen` | 3 | `params.json` | `parts/*.fs` | Génération de code |
| `cad-onshape-injector` | 4 | `output.fs` + URL Onshape | Screenshot + pièce CAO | Playwright + Chromium |
| `cad-qa` | 5 | `spec.json`, `params.json`, STL | Rapport de gate | 4 scripts Python |

### QA Gates

| Gate | Script | Vérifie |
|------|--------|---------|
| 1 | `validate_spec.py` | Complétude spec (champs, unités, plages) |
| 2 | `validate_params.py` | Cohérence physique (ratios, ajustements, standards) |
| 3 | `validate_geometry.py` | Intégrité STL (manifold, watertight, dimensions) |
| 4 | `validate_printability.py` | Printabilité FDM (surplombs, parois, volume) |

## Environnement

### Python
- **Version : 3.12** (pinnée — `jax-metal` nécessite `jaxlib 0.4.34` qui n'existe que pour CPython 3.12)
- **Isolation :** `venv` + `direnv` (activation automatique au `cd`)
- **Dépendances clés :**
  - `jax==0.4.35` + `jax-metal==0.1.1` → calculs GPU Apple Silicon
  - `playwright>=1.40` → automation navigateur Onshape
  - `trimesh>=4.0` → validation géométrique STL

### Authentification Onshape
- `.env` contient `ONSHAPE_EMAIL` et `ONSHAPE_PASSWORD`
- `cad-onshape-injector` utilise ces credentials pour le login automatique Playwright
- Session persistante dans `.browser-data/` (gitignoré)

## Stratégie de Branches Onshape

Onshape est utilisé comme un dépôt Git :
- **`main`** — branche de l'humain (ajouts manuels en features natives)
- **`ai/main`** — branche de l'IA (FeatureScript injecté uniquement)

### Règles
| Règle | Détail |
|-------|--------|
| IA n'écrit jamais dans `main` | Toujours `ai/main`, puis merge explicite |
| Humain n'écrit jamais dans `ai/main` | Modifs manuelles dans `main` ou branches personnelles |
| Un `.fs` = un Part Studio | `parts/hull.fs` → Part Studio "Hull" → géré par l'IA |
| Part Studios sans `.fs` | Ignorés par l'IA (domaine humain exclusif) |

### Workflow IA
```
JAX → parts/hull.fs → inject dans ai/main → merge → main
```

### Workflow intégration manuelle
```
1. Humain crée branche "benoit/modifs" depuis main
2. @cad "Analyse benoit/modifs"
3. L'agent lit le diff, met à jour parts/*.fs
4. L'agent injecte dans ai/main, merge → main
```

## Workflow de Conception

```
@cad "Design a 4m sailing dinghy..."

Phase 1: cad-requirements  → spec.json    ── Gate 1 ── ▶ Approbation utilisateur
Phase 2: cad-naval-math     → params.json  ── Gate 2 ── ▶ Approbation utilisateur
Phase 3: cad-featurescript-gen → parts/*.fs
Phase 4: cad-onshape-injector  → pièce CAO  ── Screenshot
Phase 5: cad-qa              → STL validé   ── Gates 3+4
```

## Contraintes Techniques

- **Pas de GUI locale** — l'agent opère en SSH. Onshape est piloté via Playwright headless.
- **Conversion d'unités** — JAX travaille en mètres, FeatureScript en millimètres. Conversion : `× 1000 → * millimeter`.
- **FeatureScript, pas de clics 3D** — le canvas WebGL d'Onshape est inaccessible à Playwright. Tout passe par injection de code dans l'éditeur FeatureScript.
- **FeatureScript = blueprint persistant** — les fichiers `.fs` dans `parts/` sont la définition canonique de la pièce, lisibles par le LLM et l'humain, versionnés dans git.
- **Gate 3 : max 3 retries** — après 3 échecs de validation géométrique, escalader à l'utilisateur.

## Conventions

- **Code, commentaires, commits :** anglais
- **Conversations avec l'utilisateur :** français
- **Artéfacts AI (agents, skills) :** anglais
- **Chemins :** toujours relatifs à la racine du projet (`.opencode/skills/...`)
- **Pas de secrets :** `.env` est gitignoré, `.env.example` est commité (sans valeurs)
