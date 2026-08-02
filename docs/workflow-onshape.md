# Workflow Onshape — Injection par session REST

## Contexte

Ce projet automatise la conception d'un bateau dans Onshape via FeatureScript :

```
manifest.json → générateur (unité du doc) → parts/*.fs
             → Feature Studio (code) → Part Studio (géométrie) → commit [AI]
```

La méthode ci-dessous a été **validée en conditions réelles** (plan Free, sans clé API).

---

## Méthode retenue — appels REST authentifiés par session

Onshape est une SPA qui parle à son propre backend REST. On s'appuie dessus :
**Playwright ne sert qu'à porter une session authentifiée** (persistée dans
`.browser-data/`) ; chaque opération CAO est un appel HTTP à l'API Onshape, pas un clic.

- **Lecture** : le cookie de session suffit.
- **Écriture** : cookie **+** en-tête `X-XSRF-TOKEN` (valeur du cookie `XSRF-TOKEN`).
  Sans lui → `401`.
- Ces appels comptent comme « session navigateur » → **hors quota** (le plan Free
  plafonne les *clés API* à 2 500 appels/an ; la session n'est pas comptée).
  Itérations illimitées.

### Pourquoi pas les autres pistes

| Piste | Verdict |
|---|---|
| Clés API REST | ❌ 2 500 appels/an sur Free — et payer n'aide pas (Standard = 2 500 aussi) |
| Pilotage UI (éditeur Monaco, clics) | ❌ fragile (sélecteurs), lent, étapes manuelles |
| Git sur Onshape | ❌ n'existe pas — Onshape a ses propres **Versions** |
| **Session + XSRF** | ✅ robuste, gratuit, hors quota |

---

## Architecture

- `manifest.json` (racine) = config maître : `document_url`, `did`, `wid`,
  `workspace_unit`, `parts[]`, `last_ai_version`.
- **1 pièce = 1 Feature Studio (code) + 1 Part Studio (géométrie rendue)**, même nom.
- Client Python : `.opencode/skills/cad-onshape-injector/scripts/onshape/`
  (`session`, `feature_studio`, `part_studio`, `versions`, `units`, `generator`,
  `manifest`).
- Entrypoint principal : `sync_project.py`.

---

## Endpoints vérifiés (base `https://cad.onshape.com`, `v10`)

| Endpoint | Usage |
|---|---|
| `GET /documents/d/{did}/w/{wid}/elements` | Lister les éléments + `lengthUnits` (unité de travail) |
| `POST /featurestudios/d/{did}/w/{wid}` | Créer un Feature Studio |
| `POST /featurestudios/d/{did}/w/{wid}/e/{eid}` | Remplacer le contenu (1 appel = 1 `.fs`) |
| `GET /featurestudios/.../e/{eid}/featurespecs` | `featureType` + `namespace` pour instancier |
| `POST /partstudios/d/{did}/w/{wid}/e/{eid}/features` | Instancier la feature → géométrie |
| `POST /metadata/.../p/{partId}` | Couleur + nom de pièce (vocabulaire partagé) |
| `POST /documents/d/{did}/versions` | **Commit** = Version immuable |

---

## Unités

- L'unité de travail = `lengthUnits` de l'élément (lue par `get_length_unit`). On la
  **respecte** ; on ne code jamais `meter` en dur.
- Deux syntaxes distinctes, à ne pas confondre :
  - **Code FeatureScript** : `2300 * millimeter` (le `*` est obligatoire).
  - **Champs de dialogue / expressions de paramètres** : `2300 millimeter` (sans `*`).
- Bonne pratique : générer **sans unité dans le corps** — exprimer les dimensions en
  fractions d'une longueur pilote (× `definition.loa`, qui porte l'unité). Seule la
  ligne des bornes nomme une unité.

---

## Commit (= Version Onshape)

Onshape n'a pas de git ; un **commit est une Version** (snapshot immuable nommé).

- **Chaque invocation de script se termine par un commit** taggé `[AI] …`. Son id va
  dans `manifest.last_ai_version`.
- Les modifs humaines sont des Versions `[HUMAN] …`. On détecte les changements
  humains en diffant l'espace de travail courant contre `last_ai_version`.
- L'API agit sous l'identité connectée → l'auteur est encodé dans le nom de la version.

---

## Cycle de travail

```
1. @cad "Design ..." → spec.json → params.json (gates 1-2)
2. Générateur → parts/*.fs (agnostique à l'unité du document)
3. sync_project.py :
     sync Feature Studio → instancie Part Studio → commit [AI]
     écrit last_ai_version + eids dans manifest.json
4. L'humain regarde / ajuste dans Onshape
5. Modif humaine → Version [HUMAN] → diff vs last_ai_version → réintégration
```

Lancement :

```bash
.venv/Scripts/python .opencode/skills/cad-onshape-injector/scripts/sync_project.py
```

(Premier lancement : login navigateur manuel une fois, puis session persistante.)

---

## Ressources

- [FeatureScript Standard Library](https://cad.onshape.com/FsDoc/library.html)
- [Onshape API Explorer (Glassworks)](https://cad.onshape.com/glassworks/explorer/)
- [API Limits](https://onshape-public.github.io/docs/auth/limits/)
