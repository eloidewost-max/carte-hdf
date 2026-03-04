# Refonte UI/UX — Design Document

## Direction

Approche hybride glassmorphism dark avec micro-animations poussées. Tous les panneaux passent en dark semi-transparent pour une cohérence visuelle totale avec le fond de carte CartoDB Dark. Le layout est réorganisé (toggle intégré au title-bar, stats panel rétractable). Les animations rendent l'app fluide et professionnelle.

Public cible : usage mixte commerciaux + présentations direction.
Contrainte : single-file HTML, publiable sur GitHub Pages.

## 1. Palette & Fondamentaux

### Couleurs panneaux
- Fond : `rgba(15,15,30,0.82)` + `backdrop-filter: blur(16px)`
- Bordure : `rgba(255,255,255,0.08)`
- Box-shadow : `0 8px 32px rgba(0,0,0,0.4)`
- Texte principal : `#e0e0e0`
- Texte secondaire : `#999`
- Séparateurs : `rgba(255,255,255,0.08)`

### Accents par mode
- Politique : `#4a90d9` (bleu)
- Surveillance : `#e8913a` (orange)
- Prospection : `#4ecdc4` (turquoise)

### Typographie
- System font stack (pas de dépendance externe)
- Base : `14px`, titres panneaux : `16px` bold, labels : `13px`
- Espacement : `padding: 16px 20px` (au lieu de `14px 16px`)

### Scrollbar custom (stats panel)
- Track : `rgba(255,255,255,0.05)`
- Thumb : `rgba(255,255,255,0.15)`, arrondi
- Largeur : `6px`

## 2. Layout & Navigation

### Title-bar (haut centré)
- Intègre le mode toggle en tabs sous le titre
- Titre `16px` bold + sous-titre `12px` secondaire
- Tabs de mode en dessous avec indicateur couleur animé (slide horizontal)
- Plus de composant `#mode-toggle` séparé

### Légende (bas gauche, flottante)
- Fond dark semi-transparent
- Texte en clair (`#e0e0e0`)
- Swatches agrandis à `18px`
- Hover : glow subtil `box-shadow` sur le swatch
- Compteurs en `#999`

### Info panel (tooltip curseur)
- Fond dark, texte clair
- Score prospection avec barre de progression colorée
- Apparition : scale-in `0.95 → 1` + fade en 150ms
- `pointer-events: none`, `position: fixed`

### Stats panel (droite)
- Bouton chevron pour replier → slide-right 250ms
- Replié : petit onglet avec icône graphique + badge nombre de communes
- Sections collapsibles avec séparateurs visuels
- Gradient fade en bas quand scrollable

### Filter bar (politique, centré haut)
- Pills en dark semi-transparent
- Texte `#ccc`, hover `#fff`
- Bouton actif : fond couleur d'accent du mode + glow

### Surv-filters (centré haut)
- Fond dark
- Sliders custom : track `rgba(255,255,255,0.1)`, filled en couleur accent orange
- Thumb rond, shadow, légèrement plus gros

## 3. Animations

### Transitions de mode
- Panneaux sortants : fade-out + translate-Y(8px) en 200ms
- Panneaux entrants : fade-in + translate-Y(-8px → 0) en 200ms
- Légende : crossfade

### Chargement initial
- Panneaux en cascade : title-bar → legend (100ms) → filter-bar (200ms)
- Chaque panneau : slide-in depuis son côté + fade

### Carte
- Changement de style : fondu couleur (transition `fillOpacity` via classe CSS)

### Info panel tooltip
- Scale `0.95 → 1` + fade en 150ms avec easing

### Score décomposition (tooltip prospection)
- Barres width animées comme des progress bars

### Mode toggle
- Indicateur actif (border-bottom) slide horizontalement vers le nouvel onglet

### Stats panel collapse
- Slide-right 250ms ease-out
- Onglet replié avec icône + badge

### Scroll indicator
- Gradient fade en bas du stats panel quand contenu déborde

### Loading screen
- Spinner en couleur accent
- Fond dark assorti (`rgba(15,15,30,0.95)`)

## 4. Responsive (mobile)

- Stats panel : bottom sheet full-width, drag-to-dismiss
- Legend : compacte, 1 colonne
- Filter pills : scroll horizontal
- Mode toggle : reste dans le title-bar, tabs plus petites
