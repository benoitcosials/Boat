# Architecture Onshape - Session Persistante et API REST

## Vue d'ensemble

L'architecture actuelle utilise une **session persistante** pour l'authentification et l'**API REST** pour toutes les opérations métier.

### Principes clés

1. **Session unique** : Un navigateur Chromium reste ouvert pendant toute la session de design
2. **Authentification persistante** : Les cookies sont sauvegardés dans `.browser-data/`
3. **API REST** : Toutes les opérations passent par l'API REST Onshape (pas d'automatisation UI)
4. **Ruff** : Linter et formateur principal (pas Pyright)

## Composants

### 1. Session Persistante (`start_session.py`)

**Rôle** : Lance et maintient un navigateur Chromium ouvert

**Fonctionnement** :
```bash
# Démarrer la session (une fois au début)
.venv/bin/python3 .opencode/skills/cad-onshape-injector/scripts/start_session.py

# Vérifier le statut
.venv/bin/python3 .opencode/skills/cad-onshape-injector/scripts/start_session.py --status

# Fermer la session (à la fin)
.venv/bin/python3 .opencode/skills/cad-onshape-injector/scripts/start_session.py --close
```

**Ce qu'il fait** :
- Lance Chromium avec `launch_persistent_context`
- Sauvegarde l'état dans `.browser-data/` (cookies, localStorage, etc.)
- Garde le navigateur ouvert jusqu'à Ctrl+C ou `--close`
- Crée un lock file `.browser-session.lock` pour éviter les sessions multiples

### 2. OnshapeSession (`onshape/session.py`)

**Rôle** : Client API REST qui réutilise les cookies sauvegardés

**Fonctionnement** :
```python
from onshape import OnshapeSession, DocumentContext

ctx = DocumentContext.from_url("https://cad.onshape.com/documents/...")

# Se connecte automatiquement avec les cookies de .browser-data/
with OnshapeSession(base_url=ctx.base_url) as session:
    # Toutes les opérations API REST
    elements = session.get(f"/documents{ctx.dw}/elements")
```

**Ce qu'il fait** :
- Lit les cookies depuis `.browser-data/`
- Extrait le token XSRF pour les requêtes POST/DELETE
- Fait des appels API REST via `requests`
- Ne lance PAS de navigateur

### 3. Clients API REST

Tous les clients utilisent `OnshapeSession` pour communiquer avec Onshape :

| Client | Rôle |
|--------|------|
| `FeatureStudioClient` | Créer/modifier des Feature Studios, injecter du FeatureScript |
| `PartStudioClient` | Créer des Part Studios, instancier des features, gérer les métadonnées |
| `CommentsClient` | Créer/lire/résoudre des commentaires |
| `VersionsClient` | Créer des versions (commits) |

**Exemple** :
```python
from onshape import FeatureStudioClient, PartStudioClient

studios = FeatureStudioClient(session, ctx)
parts = PartStudioClient(session, ctx)

# Injecter du FeatureScript
fs_eid = studios.sync("Hull", fs_text)

# Instancier dans un Part Studio
ps_eid = parts.ensure("Hull")
parts.instantiate(ps_eid, feature_type, namespace, "Hull 1", params)
```

## Architecture des Scripts

### Utilisation automatique des cookies

Tous les scripts réutilisent automatiquement les cookies sauvegardés dans `.browser-data/` via `OnshapeSession`. Pas besoin d'option spéciale.

**Exemple** :
```python
from onshape import OnshapeSession, DocumentContext

ctx = DocumentContext.from_url("https://cad.onshape.com/documents/...")

# Se connecte automatiquement avec les cookies de .browser-data/
with OnshapeSession(base_url=ctx.base_url) as session:
    # Toutes les opérations API REST
    elements = session.get(f"/documents{ctx.dw}/elements")
```

## Flux de Travail Typique

### 1. Démarrage

```bash
# Terminal 1 : Démarrer la session
.venv/bin/python3 start_session.py

# Le navigateur s'ouvre sur https://cad.onshape.com
# Vous pouvez voir le navigateur en remote (iMac)
```

### 2. Utiliser les scripts

Tous les scripts réutilisent automatiquement les cookies de `.browser-data/` :

```bash
# Lister les commentaires (utilise les cookies sauvegardés)
.venv/bin/python3 manage_comments.py list

# Sync le projet
.venv/bin/python3 sync_project.py

# Diagnostiquer les erreurs
.venv/bin/python3 diagnose_errors.py
```

**Implémentation** :
```python
# Tous les scripts utilisent OnshapeSession qui lit automatiquement les cookies
with OnshapeSession(base_url=ctx.base_url) as session:
    # Toutes les opérations API REST
    elements = session.get(f"/documents{ctx.dw}/elements")
```

### 3. Fin de session

```bash
# Terminal 1 : Ctrl+C ou
.venv/bin/python3 start_session.py --close
```

## Fichiers Importants

| Fichier | Rôle |
|---------|------|
| `.browser-data/` | Données persistantes du navigateur (cookies, login) |
| `.browser-session.lock` | Lock file pour éviter les sessions multiples |
| `manifest.json` | Configuration du projet (URL document, parts, paramètres) |
| `parts/*.fs` | Fichiers FeatureScript source |

## Avantages de l'Architecture

1. **Performance** : Pas de lancement de navigateur à chaque script
2. **Fiabilité** : API REST plus stable que l'automatisation UI
3. **Transparence** : Vous pouvez voir le navigateur en temps réel
4. **Simplicité** : Une seule session, pas de confusion
5. **Quota API** : Les appels via session navigateur ne comptent pas dans le quota

## Dépannage

### "No session is running"

```bash
# Démarrer une session
.venv/bin/python3 start_session.py
```

### "A session is already running"

```bash
# Fermer la session existante
.venv/bin/python3 start_session.py --close

# Ou supprimer manuellement le lock
rm .browser-session.lock
```

### Erreurs d'authentification

```bash
# Vérifier que .browser-data/ existe
ls -la .browser-data/

# Si vide ou corrompu, supprimer et recommencer
rm -rf .browser-data/
.venv/bin/python3 start_session.py
# Se connecter manuellement dans le navigateur
```

## Ruff Configuration

Le projet utilise **Ruff** comme linter et formateur principal.

**Configuration** : `ruff.toml`

```toml
target-version = "py312"
line-length = 100

extend-exclude = [
    ".venv",
    ".browser-data",
    ".opencode/archive",
    ".playwright-mcp",
    "tmp",
]

[lint]
select = ["E", "W", "F", "I", "UP", "B"]
ignore = ["E501"]
```

**Utilisation** :
```bash
# Linter
.venv/bin/ruff check .

# Formater
.venv/bin/ruff format .

# Auto-fix
.venv/bin/ruff check --fix .
```

**Pourquoi Ruff et pas Pyright ?**
- Plus rapide
- Moins verbeux
- Pas de faux positifs sur les imports dynamiques
- Suffisant pour ce projet (pas de type checking strict nécessaire)

## Migration depuis l'Ancienne Architecture

### Ancienne approche (obsolète)

```python
# Chaque script lançait son propre navigateur
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto("https://cad.onshape.com")
    # ... automatisation UI ...
```

### Nouvelle approche

```python
# Réutilise la session persistante
with OnshapeSession(base_url=ctx.base_url) as session:
    elements = session.get("/documents/.../elements")
    # ... API REST ...
```

## Bonnes Pratiques

1. **Toujours démarrer la session** avant d'utiliser les scripts
2. **Ne pas fermer le navigateur manuellement** (utiliser `--close`)
3. **Vérifier le statut** avec `--status` en cas de doute
4. **Commiter les changements** dans `manifest.json` après chaque sync

## Limitations

1. **Une seule session à la fois** (lock file)
2. **Navigateur doit rester ouvert** (pas de headless pour le moment)
3. **Login manuel la première fois** (pas d'auto-login)
4. **Pas de multi-utilisateurs** (une seule session par machine)

## Futures Améliorations

- [ ] Support headless pour la session persistante
- [ ] Auto-login via variables d'environnement
- [ ] Multi-sessions (plusieurs documents en parallèle)
- [ ] Intégration avec d'autres outils CAD
- [ ] Export automatique des erreurs vers un fichier log
