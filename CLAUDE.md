# CLAUDE.md — Carte de prospection Vizzia (Hauts-de-France)

> Fichier de contexte lu automatiquement par Claude Code au démarrage de chaque session.
> Il décrit le projet, les règles de travail, la structure des données et la feuille de route.

---

## Qui je suis (l'utilisateur)

Je m'appelle Eloi, commercial terrain chez Vizzia. **Je ne suis PAS développeur.** Je comprends la logique mais pas le code. Il faut donc :
- M'expliquer les choses simplement, sans jargon.
- Bien distinguer quand tu parles du TERMINAL vs d'autre chose.
- Y aller étape par étape, en prévenant tout risque de perte de données.
- Toujours tester avant de déployer, et faire des sauvegardes.

Mon équipe : **Étienne** (BDR/associé, travaille avec moi sur les Hauts-de-France) et **Sami** (nouveau, s'occupera de la région Auvergne-Rhône-Alpes).

---

## Le projet en bref

Une **carte web de prospection commerciale** pour cibler et suivre les communes des Hauts-de-France (départements 02, 59, 60, 62, 80).

- **Fichier unique** : `hdf-map.html` (~3,3 Mo), tout est dedans (HTML + CSS + JS + données).
- **Techno** : Leaflet.js (carte) + Firebase Firestore (données temps réel via onSnapshot).
- **Hébergement** : GitHub Pages. Dépôt `eloidewost-max/carte-hdf`, remote `carte-hdf`, branche locale `feature/carte-v2` poussée sur `main`.
- **URL publique** : https://eloidewost-max.github.io/carte-hdf/
- **Chemin local** : `/Users/eloi/Desktop/Artefact Vizzia/carte-politique-main/` (⚠️ contient un espace).

---

## Workflow de déploiement (IMPORTANT)

Règle d'or : **tester le JS AVANT de déployer.** Ne jamais déployer un fichier dont le JavaScript n'a pas été validé.

Procédure sûre pour toute modification :
1. Faire une sauvegarde du fichier avant modif : `cp hdf-map.html hdf-map-AVANT-[nom].html`
2. Modifier `hdf-map.html`.
3. Valider le JS avant de déployer. Si erreur → NE PAS déployer, corriger d'abord. ⚠️ `node` n'est PAS installé sur cette machine : utiliser JavaScriptCore (`jsc`, fourni avec macOS : `/System/Library/Frameworks/JavaScriptCore.framework/Versions/Current/Helpers/jsc`). Extraire le JS des `<script>`, l'entourer de `if(false){ ... }` (analyse syntaxique sans exécution → pas d'erreur parasite type "L is not defined"), puis `jsc fichier.js` (sortie vide = OK). Valider aussi les gros blocs de données injectés avec `python3 -c "import json; json.loads(...)"`.
4. Tester en local : `open "hdf-map.html"` et vérifier le comportement.
5. Déployer avec l'alias `deploycarte`.

L'alias `deploycarte` fait :
```
cd "/Users/eloi/Desktop/Artefact Vizzia/carte-politique-main" && cp hdf-map.html index.html && git add . && git commit -m "update carte" && git push carte-hdf HEAD:main --force
```

Notes de déploiement :
- GitHub Pages échoue parfois temporairement ("try again later") → relancer avec `git commit --allow-empty -m "relance" && git push carte-hdf HEAD:main --force`.
- Recharger la carte en ligne avec Cmd+Shift+R.
- L'aperçu HTML dans le chat Claude affiche des erreurs "firebase/L is not defined" → NORMAL (l'aperçu bloque les libs externes), ça ne teste pas la validité réelle. Toujours tester en local.

---

## Filet de sécurité en place

- Tag Git `v1-stable` = point de retour du code (avant la refonte).
- Sauvegarde JSON des données (statuts + visites + rdv) exportable via le bouton "💾 Sauvegarder une copie" dans l'app.
- Nombreux fichiers `.bak` d'anciennes versions (ménage possible, pas urgent).

---

## Structure des données

### `HDF_DATA` — les communes cliquables (~2760)
Objet `{ "codeINSEE": { n, lat, lng, pop, ... } }`. Ex :
`"80021": { "n": "Amiens", "lat": 49.8942, "lng": 2.2958, "pop": 134057, ... }`
Le code INSEE (clé) est central : 2 premiers chiffres = département.

### `COMMUNES_GEO` — géométries cliquables
GeoJSON, properties `{ "codgeo": "02001" }`.

### `HDF_BG_GEO` — couche de fond (1034 communes)
Contours gris clair `#d0d0d0`, properties `{ codgeo }`. Communes hors cible : les **<200 hab** (880) et les **≥7000 hab** (147 grandes villes) + 7 codes résiduels.

### `GRANDES_VILLES_GEO` / `GRANDES_VILLES_DATA`
Les 147 grandes villes (≥7000 hab), rendues cliquables : gris foncé `#8a8a8a`, popup nom+population, noms affichés.

### `PETITES_COMMUNES_GEO` / `PETITES_COMMUNES_DATA` (fait le 2026-07-05)
Les 880 petites communes (<200 hab), rendues cliquables : gris moyen `#b5b5b5`, popup nom+population, SANS statut ni lien Firebase (calque isolé). 7 codes INSEE fusionnés/introuvables restent en fond inerte (62743, 80830, 02311, 62461, 02077, 62549, 59070). Données nom+pop récupérées via l'API `geo.api.gouv.fr` (le fichier `communes-plus7000.json` mentionné avant n'existait plus).

### Toggle "hors-cible" (bouton unique, fait le 2026-07-05)
Un seul bouton (`toggleHorsCible`) masque/affiche d'un coup TOUT le hors-cible : fond gris + grandes villes (+ leurs noms) + petites communes. **Masqué par défaut** au chargement (carte épurée = seulement les communes cibles 200–7000 hab). Remplace l'ancien bouton "grandes villes".

### Les 6 statuts commerciaux (couleurs)
- prioritaire `#eab308` (jaune) · rdv_avenir `#93c5fd` (bleu clair) · rdv_fait `#1d4ed8` (bleu foncé) · signature `#f97316` (orange) · signe `#22c55e` (vert) · perdu `#ef4444` (rouge)
- Définis dans la liste centrale `STATUTS` (tout en dérive : légende, boutons, compteurs, labels).
- Simplification 8→6 faite le 2026-07-05 : suppression de "prospectee" (communes redevenues neutres) et fusion de "perdu_rdv" dans "perdu" (label unique "Perdu"). Une fonction `normalizeStatuts()` traduit à la lecture Firebase (`perdu_rdv`→`perdu`, `prospectee` retiré) + nettoyage unique de la base au chargement.

### Firebase
projectId "communes-hdf". Documents : `statuts/communes`, `statuts/visites`, `statuts/rdv`.

---

## Comportements clés déjà en place

- **Clic simple** sur commune → ouvre le détail, NE bouge PAS la carte.
- **SHIFT + clic** → recentre (zoom doux, maxZoom 10).
- **CMD + clic** → trajet (multitrajets, lignes pointillées, temps/distance OSRM).
- **Recherche** (barre) → logique par DÉPARTEMENT : même département que la recherche précédente → la commune clignote (contours jaunes) sans bouger la carte ; département différent → recentrage zoom léger (maxZoom 10.5).
- Filtre département (pastilles 02/59/60/62/80).
- Filtre population : existe dans le code mais plus accessible via l'UI (à ré-exposer un jour) — sert à cibler des tailles de communes pour les exports.
- Sélecteur de date pour les rdv + surbrillance même jour.
- **Clic sur petite commune (<200) ou grande ville (≥7000)** → popup simple nom+population (hors cible, aucun statut). Ces couches sont masquées par défaut (bouton "hors-cible").

---

## Feuille de route (chantiers restants, ordre logique)

- ✅ **Petites communes (<200 hab, 880) cliquables** — FAIT le 2026-07-05 (voir `PETITES_COMMUNES_GEO` + toggle hors-cible dans Structure des données).
- ✅ **Simplification statuts 8→6** — FAIT le 2026-07-05 (voir section statuts).

1. **Surcouches thématiques** : filtres à pastilles cumulables, open data (éoliennes d'abord, puis 5G…). Ajouter un critère = ajouter une donnée, pas recoder.
2. **Pont HubSpot → carte** (gros morceau, carburant du reste) : faire remonter les rdv HubSpot automatiquement. Voir cadrage détaillé.
3. **Vue Agenda** : remplacer les onglets inutiles (Politique, Connectivité, ex-ICP) par Prospection + Agenda. Sélection d'une plage de dates → affiche les communes avec rdv sur la période (physiques en couleur vive, visios en clair, communes actives à potentiel en gris uni sauf perdus). Débouché du pont HubSpot.
4. **Duplication Auvergne-Rhône-Alpes** : 03 Allier, 63 Puy-de-Dôme, 15 Cantal, 43 Haute-Loire, 07 Ardèche. Carte séparée + base Firebase propre.

---

## Pont HubSpot — points clés (chantier majeur)

Objectif : les rdv saisis dans HubSpot remontent automatiquement sur la carte (fini la double saisie). HubSpot = source de vérité, la carte lit.

Validé techniquement :
- Fiches commune HubSpot (objet Company) ont le champ `code_commune_insee` = même clé que la carte.
- Rdv = objets Meeting avec `hs_meeting_start_time` (date), `hs_meeting_outcome` (SCHEDULED/COMPLETED/CANCELED/NO_SHOW), `hubspot_owner_id` (le propriétaire, permet de filtrer par personne).
- Chaîne Meeting → Company → code_commune_insee fiable.

**Physique vs visio** : le champ **Location** du meeting (`hs_meeting_location_type`) fait foi :
- `ADDRESS` (In-person) = physique → crée une visite terrain.
- `VCE` (Google Meet / Teams) = visio → PAS de visite terrain.
- Plus fiable que le titre. Dépend du remplissage rigoureux du champ (discipline de saisie à imposer à l'équipe).

Points à trancher avant de coder (règles déterministes obligatoires, sinon risque que toutes les communes changent de couleur d'un coup) :
- **Machine à états des statuts** : Prioritaire → (rdv physique pris) → Rdv à venir ; Rdv à venir → (décalé) → Rdv à venir (nouvelle date) ; Rdv à venir → (annulé/sans suite) → retour Prioritaire ; Rdv à venir → (fait) → Rdv fait ; Rdv fait → (signature) → Signé. Définir la hiérarchie de priorité entre statuts.
- **Cas multi-rdv** : une commune vue plusieurs fois peut être "Rdv fait" ET avoir un nouveau "Rdv à venir". Ne pas perdre l'historique. Piste : couleur simple + détail riche au clic (historique HubSpot) + éventuel badge "déjà visitée".
- **Import ponctuel vs synchro vivante** ; gestion annulations/décalages ; quels rdv (les miens ? HDF only ? à venir only ?) ; meetings sans commune associée.
- **Protocole de saisie BDR** : la carte n'est fiable que si Étienne, Sami et moi remplissons bien les champs HubSpot (Location, outcome). Fiche de consignes à créer.

Note technique : `query_crm_data` (SQL HubSpot) échoue faute de scope `reporting-base-read` ; utiliser `search_crm_objects`.

---

## Dimension équipe (à anticiper dans l'architecture)

- Cartes de prospection séparées par territoire (HDF / ARA), bases Firebase distinctes.
- MAIS besoin d'une vue Agenda partagée (au moins déplacements physiques) pour éviter les conflits : ex. que Sami ne cale pas un rdv physique à Clermont le jour où je suis en déplacement dans l'Oise. Faisable via `hubspot_owner_id` (filtrer/colorer par personne).

---

## Décisions de conception actées

- Garder séparés : **statuts carte** (ressenti terrain manuel, précieux) et **stages deals HubSpot** (avancement officiel). Complémentaires.
- **Ne pas afficher les deals** sur la carte de prospection (besoin non avéré).
- Le pont HubSpot concerne **les rdv**, pas les deals.
- Chaque vue a son propre langage de couleurs (ne pas surcharger).

---

## Rappels pratiques

- Vider régulièrement le dossier Téléchargements des vieux `hdf-map*.html` (Chrome crée des `_1`, `_2`… qui ont déjà causé le déploiement d'une mauvaise version).
- Révoquer les anciens tokens GitHub qui ont fuité dans d'anciennes sessions.
