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
│   │   ├── cad-onshape-injector/ # Phase 4 : injection REST (session) → Onshape
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
| `cad-onshape-injector` | 4 | `manifest.json` + `parts/*.fs` | Pièce CAO + commit `[AI]` | Session REST (Playwright porte la session) |
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
- **Login manuel une fois** dans la fenêtre Playwright ; la session est ensuite persistée dans `.browser-data/` (gitignoré).
- Écritures API : cookie de session **+** en-tête `X-XSRF-TOKEN` (valeur du cookie `XSRF-TOKEN`). Ces appels sont **hors quota** (pas de clé API).
- Aucun secret ne transite par le LLM ; l'utilisateur saisit son mot de passe directement.

## Versionnement Onshape (commits)

Onshape n'a pas de git — un **commit est une Version** (snapshot immuable nommé).

### Règles
| Règle | Détail |
|-------|--------|
| Commit à chaque run | Chaque invocation de script crée une Version `[AI] …` ; l'id va dans `manifest.last_ai_version` |
| Auteur encodé dans le nom | L'API agit sous l'identité connectée → `[AI]` (script) vs `[HUMAN]` (édition manuelle) |
| Un `.fs` = un Feature Studio + un Part Studio | `parts/hull.fs` → Feature Studio + Part Studio "Hull" |
| Part Studios hors manifeste | Domaine humain exclusif — jamais touchés par l'IA |
| Le LLM ne lance jamais git | L'historique git de `parts/*.fs` est piloté par le prompt/pipeline |

### Workflow IA
```
manifest.json → générateur → parts/hull.fs → sync (Feature Studio + Part Studio) → commit [AI]
```

### Workflow intégration manuelle
```
1. L'humain modifie une pièce dans Onshape (Version [HUMAN])
2. @cad diffe l'état courant contre last_ai_version
3. L'agent réintègre les changements dans le générateur / parts/*.fs
4. sync_project.py → commit [AI]
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

- **Pas de GUI locale** — l'agent opère en SSH. Onshape est piloté par **appels REST** via une session navigateur (Playwright porte la session, headless possible).
- **Unités** — lire et **respecter le workspace unit** du document ; générer de façon agnostique (fractions × `definition.<len>`). Code FeatureScript : `n * unit` ; expressions de dialogue : `n unit` (sans `*`).
- **Pas de clics 3D ni d'éditeur UI** — tout passe par des appels REST : contenu de Feature Studio, instanciation dans le Part Studio, métadonnées (couleur/nom), Versions (commits).
- **FeatureScript = blueprint persistant** — les fichiers `.fs` dans `parts/` sont la définition canonique de la pièce, lisibles par le LLM et l'humain, versionnés dans git.
- **Gate 3 : max 3 retries** — après 3 échecs de validation géométrique, escalader à l'utilisateur.

## Conventions

- **Code, commentaires, commits :** anglais
- **Conversations avec l'utilisateur :** français
- **Artéfacts AI (agents, skills) :** anglais
- **Chemins :** toujours relatifs à la racine du projet (`.opencode/skills/...`)
- **Pas de secrets :** `.env` est gitignoré, `.env.example` est commité (sans valeurs)
