# Optimist — dossier de conception (règles de classe & modèle paramétrique)

> Document de référence pour le modèle CAO de la coque Optimist du projet Boat.
> Objectif : consigner les **contraintes officielles sourcées** et le **modèle
> paramétrique** qui en découle, en distinguant clairement ce qui est
> **règle de classe** de ce qui est **interprétation de conception**.

## 1. Sources

| Source | Contenu | Accès |
|---|---|---|
| **IODA — International Optimist Class Rules 2022** (`2022 IODA-Rules-Final March 1_22`) | Règles de jauge officielles (texte + gabarits) | optiworld.org (PDF, lu via pdf.js) |
| **World Sailing — Optimist class page** | Fiche classe, plan de formes indicatif, longueur coque 2,3 m | sailing.org/classes/optimist |
| **Wikipedia — Optimist (dinghy)** | Fiche récapitulative (bau, LWL, tirant d'eau, poids, voile) | en.wikipedia.org/wiki/Optimist_(dinghy) |
| **Plans d'origine 1948 (C. Mills)** | Plans CTP d'origine, cotés (impérial) — scans | stexboat.com/boat_building/plans/opti1948 (copie locale : `docs/optimist-plans-1948/`) |

**Constat important :** les règles de classe **ne contiennent pas de table
d'offsets** ni de valeurs de bau/tableaux. La forme exacte de la coque est
définie par le **« Official Plan »** (document contrôlé, non public). Les règles
ne fournissent que l'**enveloppe**, des **points de contrôle**, des **tolérances**
et des **gabarits de mesure** (le « Standardized Sheerline / Edge-Zone Finder »
est un outil de contrôle, pas un plan de formes).

## 2. Système de coordonnées (jauge)

- **Origine** : coin **inférieur** du **tableau arrière** (aft transom lower corner).
- **X** : vers l'**avant** (0 → ~2300 mm).
- **Y** : transversal (demi-largeurs ± depuis l'axe).
- **Z** : vers le **haut**.
- La coque est représentée **inversée** dans les planches de jauge.

## 3. Contraintes de classe (sourcées, avec référence CR)

| Grandeur | Valeur | Réf. |
|---|---|---|
| Longueur hors-tout (hors ferrures de safran) | **2300 mm ±7**, mesurée au point 4 (sheerline) | CR 3.2.2.5 |
| Tolérance standard | **±2 mm** sauf indication ; `max`/`min` sans tolérance | CR 3.2.2.1 |
| Base-line (réf. quille/rocker) | horizontale passant à **110 mm** (X=28) et **162 mm** (X=2121) sous la coque (axe), mesuré depuis le plan vertical du coin bas du tableau AR | CR 3.2.2.3 |
| Upper base-line | horizontale à **63 mm** au-dessus du haut du tableau **AR** et **23 mm** au-dessus du haut du tableau **AV** | CR 3.2.2.3 |
| Tableau AR | **perpendiculaire** à la base-line (déviation max **5 mm** au bord haut) | CR 3.2.2.4 |
| Planéité fond (chine à chine) | règle ≤ **5 mm**, aucun creux | CR 3.2.2.6 |
| Planéité fond (règle 300 / 150 mm) | ≤ **4 mm** / ≤ **2 mm** | CR 3.2.2.8 |
| Planéité flancs | règle ≤ **5 mm** | CR 3.2.2.7 |
| Puits de dérive (fente fond) | longueur **330 mm ±4**, largeur **17 mm ±1**, extrémités semi-circulaires | CR 3.2.2.10-11 |
| Rayons de coque | fond/flanc, fond/tableau AV, flanc/tableau AV : **R10 mm** ; **tableau AR : aucun rayon** | CR 3.2.2.12 |
| Blocs d'écoute (fond) | à **786 mm** et **894 mm ±5** de la face avant du tableau AR | CR 3.2.6.1(a) |
| Construction | 3 composants moulés (GRP) : coque, ensemble liston/banc de mât, puits de dérive | CR 3.2.3.1 |

**Interprétation clé (rocker / tableaux) :**
- L'axe du **fond** (quille) est à **+110 mm** (près de la poupe, X=28) et **+162 mm**
  (près de l'étrave, X=2121) au-dessus de la base-line → le fond **remonte vers
  l'avant** (rocker plus marqué à l'étrave).
- L'**étrave est ~40 mm plus haute** que la poupe (63 − 23 mm au-dessus des tableaux).
- Panneaux **plats à ±4-5 mm** → coque **développable à bouchain vif** (surfaces
  réglées), pas de forme libre.

## 4. Dimensions publiées (World Sailing / Wikipedia) — hors règles CR

> Valeurs indicatives (fiche classe), à confirmer contre l'Official Plan.

| Grandeur | Valeur |
|---|---|
| Bau max (au liston) | ~**1130 mm** (Wikipedia : 1120 mm) |
| Longueur de flottaison (LWL) | ~2180 mm |
| Tirant d'eau coque / dérive baissée | 130 mm / 840 mm |
| Poids coque (mini classe) | **35 kg** → cible densité matériau |
| Voile / mât | 3,3 m² / 2,26 m |

## 5. Ce qui n'est PAS public

- Table d'offsets complète (largeur de fond, demi-bau par station).
- Largeurs et hauteurs exactes des deux tableaux.
- Formes de sections (body plan), ligne de bouchain détaillée.

→ Ces valeurs relèvent de l'**Official Plan** contrôlé. Le modèle ci-dessous les
**interpole** de façon fidèle (pram développable) en respectant toutes les
contraintes de §3, et **marque explicitement** ces valeurs comme *interprétation*.

## 6. Modèle paramétrique proposé

**Topologie** : pram à **bouchain vif**, panneaux **développables** :
fond (plat, à rocker) + 2 flancs (plats, évasés) + 2 tableaux (rakés) + liston.

**Paramètres — contraintes de classe (sourcés) :**
- `loa = 2300 mm`
- `keel_z(X=28) = 110 mm`, `keel_z(X=2121) = 162 mm` au-dessus base-line (rocker)
- `transom_aft_top`, `transom_fwd_top` calés via upper base-line (Δ ≈ 40 mm)
- `daggerboard_slot = 330 × 17 mm`
- `mainsheet_x = 786 / 894 mm` (repères pont, non structurants pour la carène)

**Paramètres — interprétation (à valider, non publics) :**
- `beam_max ≈ 1130 mm` (au liston, section maîtresse)
- `bottom_width[station]` — largeur du fond (à définir, ~ 500-650 mm au maître-bau ?)
- `transom_aft_w_bottom / w_top`, `transom_fwd_w_bottom / w_top`
- `chine_height[station]`, `sheer_height[station]`
- `n_stations` (lissage), `bulkhead_x` (~ milieu), `daggerboard_x`

**Construction (FeatureScript) :** lignes de **quille (rocker)**, **bouchain**,
**liston** définies à quelques stations → loft **réglé** du fond + des flancs +
2 tableaux → solide à bouchain vif. Puis (phase matériaux) `opShell` pour
l'épaisseur, et assignation `Matériau` (densité) → Masse/CG natifs.

## 7. Plans d'origine 1948 (Clark Mills) — offsets réels

L'Optimist a été conçu pour l'auto-construction en **contreplaqué** ; les plans
d'origine (1948) sont **cotés** (unités **impériales**) et donnent de vrais
offsets, à distinguer de la jauge stricte one-design moderne (standardisée 1960,
stricte 1995). Scans conservés dans `docs/optimist-plans-1948/`.

| Fichier | Contenu |
|---|---|
| `all_draw.jpg` | **Planche complète** (photo, 4000×3000) — vue d'ensemble (un peu floue, à améliorer) |
| `hull_1.jpg` | **FIG.4 Top view** (plan) — bau, largeurs tableaux, cloison, puits |
| `hull_2.jpg` | Couples (A/B/C), tableaux, élévations |
| `base.jpg` | FIG.1 base de montage — plan (positions couples) |
| `base2.jpg` | FIG.1/3 base — profil (entraxes, rocker) |
| `m_step.jpg` | Pied de mât |
| `optimist.gif` | Vue d'ensemble |

**Cotes lues (1948, impérial → mm indicatifs) :**
- Entraxes des couples : **A→B ≈ 3'1¾" (965 mm)**, **B→C ≈ 4'7" (1397 mm)** → longueur ≈ 2360 mm.
- **Bau max au gunnel ≈ 42" (≈ 1067 mm)** (le pram d'origine est un peu plus étroit que le 1130 mm moderne).
- Tableau AV (bow) : demi-largeurs ~7¼"/7½", largeur ~11".
- Demi-largeur du **fond** au tableau AR ≈ **8"**.
- Longueur de référence pont/cloison ≈ 38½", zone puits de dérive ≈ 17".
- Bordé : **¼" plywood** (côtés) ; trou de mât **2" dia. max**.

> ⚠️ Ces cotes sont **relevées à la main** sur des scans et en **impérial** ; à
> recouper section par section (hull_1/hull_2) avant génération. Écart assumé
> avec le one-design moderne (bau 42" vs ~1130 mm).

## 8. Historique
- 2026-08-02 : création. Données de jauge extraites du PDF IODA 2022 (pdf.js),
  recoupées avec World Sailing et Wikipedia. Offsets détaillés non publics → à
  interpréter puis valider.
