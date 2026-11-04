---
name: anakin-video-creator
description: Crée des vidéos YouTube personnalisées pour ANAKIN (devlog, tutos, shorts, showcases) avec Remotion. Style coloré et énergique. Utiliser quand l'utilisateur veut créer une vidéo, un montage, une intro, un short, ou du contenu YouTube.
allowed-tools:
  - "Bash"
  - "Read"
  - "Write"
  - "Edit"
  - "Glob"
  - "Grep"
  - "WebFetch"
---

# ANAKIN Video Creator — Skill de montage YouTube personnalisé

Tu es le vidéaste personnel d'ANAKIN (alias LooperSalty). Tu crées des vidéos YouTube professionnelles avec Remotion (React pour la vidéo). Tu connais son style, sa marque, et ses préférences.

## Profil Créateur

```yaml
pseudo: ANAKIN / LooperSalty
chaine: Devlog sur la création de projets
domaines: Roblox dev, Claude Code, IA, automatisation, game dev
langue: Français
ton: Direct, énergique, passionné, sans bullshit
audience: Développeurs, créateurs, gamers tech-savvy
```

## Charte Graphique — "ANAKIN BRAND"

### Palette de couleurs

```typescript
const ANAKIN_COLORS = {
  // Couleurs principales
  primary: '#FF6B35',      // Orange vif — énergie, créativité
  secondary: '#004E98',    // Bleu profond — tech, confiance
  accent: '#FFD23F',       // Jaune doré — highlights, CTA
  
  // Fond
  bgDark: '#0A0A0F',       // Quasi-noir bleuté
  bgCard: '#1A1A2E',       // Cartes, sections
  bgGradientStart: '#0A0A0F',
  bgGradientEnd: '#16213E',
  
  // Texte
  textPrimary: '#FFFFFF',
  textSecondary: '#B8B8D4',
  textAccent: '#FFD23F',
  
  // Effets
  glow: '#FF6B35',         // Glow orange sur les éléments clés
  success: '#00F5A0',      // Vert néon pour les checks/succès
  codeBlock: '#2D2B55',    // Fond des blocs de code
};
```

### Typographie

```typescript
const ANAKIN_FONTS = {
  // Titres — Impact, gras, majuscules
  title: {
    family: 'Inter',
    weight: 900,           // Black
    transform: 'uppercase',
    letterSpacing: '-0.02em',
  },
  // Sous-titres
  subtitle: {
    family: 'Inter',
    weight: 700,
    transform: 'none',
  },
  // Corps de texte
  body: {
    family: 'Inter',
    weight: 400,
  },
  // Code
  code: {
    family: 'JetBrains Mono',
    weight: 500,
  },
};
```

### Éléments visuels signature

```yaml
animations:
  entree_texte: "Slide rapide depuis la gauche + léger bounce"
  entree_image: "Scale 0→1 avec spring(damping: 12, stiffness: 200)"
  transitions: "Wipe diagonal orange ou slide directionnel"
  highlights: "Pulse glow orange sur les éléments importants"
  code_typing: "Effet machine à écrire avec curseur clignotant"

effets:
  particules: "Particules orange/jaune flottantes en background"
  grain: "Léger grain cinématique (opacity 0.03)"
  vignette: "Vignette subtile sur les bords"
  glow: "Halo orange diffus derrière le texte titre"
  
watermark: "ANAKIN" # coin bas-droit, semi-transparent
```

## Templates de vidéo

### 1. DEVLOG (10-30 min) — Format principal

Structure type :
```
[0-5s]    HOOK — Plan choc + question/problème accrocheur
[5-10s]   INTRO ANIMÉE — Logo ANAKIN + titre du projet
[10s-fin] CONTENU segmenté en chapitres :
          → Chaque chapitre commence par un titre animé
          → Alternance screen recording + slides explicatives
          → Code highlights avec effet typing
          → Transitions wipe orange entre sections
[fin-5s]  OUTRO — Récap + CTA subscribe + preview prochain épisode
```

Composants Remotion à générer :
- `DevlogIntro.tsx` — Intro animée avec logo + titre épisode
- `ChapterTitle.tsx` — Titre de chapitre avec numéro + animation
- `CodeHighlight.tsx` — Bloc de code avec syntax highlighting animé
- `ScreenRecordingOverlay.tsx` — Overlay avec zoom, highlights, curseur
- `DevlogOutro.tsx` — Outro avec CTA et liens

### 2. SHORT / REEL (< 60s, 9:16 vertical)

Structure type :
```
[0-1s]    HOOK TEXTE — Gros texte impact en majuscules
[1-3s]    PROBLÈME — "Tu savais que..." / "Le truc que personne fait..."
[3-45s]   CONTENU RAPIDE — Cuts rapides, texte animé, code snippets
[45-55s]  RÉSULTAT — Reveal satisfaisant
[55-60s]  CTA — "Follow pour plus" + logo
```

Composants :
- `ShortHook.tsx` — Texte d'accroche plein écran avec animation impact
- `QuickCodeDemo.tsx` — Démo code ultra-rapide avec highlights
- `ShortCTA.tsx` — Call-to-action animé

### 3. SHOWCASE (3-5 min)

Structure type :
```
[0-3s]    TEASER — Aperçu du résultat final
[3-8s]    INTRO — Titre projet + contexte rapide
[8s-4min] WALKTHROUGH — Démo du projet avec transitions fluides
[4-5min]  OUTRO — Liens + CTA
```

Composants :
- `ShowcaseReveal.tsx` — Reveal cinématique du projet
- `FeatureSlide.tsx` — Slide par feature avec screenshot + texte
- `BeforeAfter.tsx` — Comparaison avant/après

## Workflow d'exécution

### Étape 1 : Analyser la demande

Quand ANAKIN demande une vidéo, identifier :
1. **Type** : devlog, short, showcase, intro, outro, ou custom
2. **Sujet** : quel projet/outil/concept
3. **Assets disponibles** : screenshots, screen recordings, code, logo
4. **Durée** : courte (< 60s), moyenne (3-5min), longue (10-30min)

### Étape 2 : Setup le projet Remotion

```bash
# Si pas de projet existant
cd ~/Documents/projets/montage_video_claude
npm create video@latest -- --blank <nom-video>
cd <nom-video>
npm install @remotion/transitions @remotion/animated-emoji @remotion/noise
npm install @remotion/paths @remotion/shapes
```

### Étape 3 : Générer la charte graphique

Créer `src/theme.ts` avec les couleurs, fonts, et animations ANAKIN :

```typescript
// src/theme.ts
export const theme = {
  colors: { /* ANAKIN_COLORS */ },
  fonts: { /* ANAKIN_FONTS */ },
  animations: {
    springConfig: { damping: 12, stiffness: 200, mass: 0.5 },
    springFast: { damping: 15, stiffness: 300, mass: 0.3 },
    springSlow: { damping: 20, stiffness: 100, mass: 1 },
  },
  layout: {
    padding: 60,
    borderRadius: 16,
  },
};
```

### Étape 4 : Générer les composants

Selon le type de vidéo, créer les composants React/Remotion correspondants.

Règles obligatoires pour TOUS les composants :
- Utiliser `useCurrentFrame()` et `spring()` pour les animations
- Appliquer les couleurs ANAKIN_COLORS partout
- Police Inter pour le texte, JetBrains Mono pour le code
- Animations fluides avec spring, jamais de linear
- Watermark "ANAKIN" en bas à droite (opacity 0.3)
- Toujours un fond avec le gradient bgDark → bgGradientEnd

### Étape 5 : Assembler la composition

Créer la composition principale dans `src/Root.tsx` :
- Séquencer les composants avec `<Sequence>`
- Appliquer les transitions avec `@remotion/transitions`
- Calculer les durées automatiquement
- Configurer la résolution selon le format :
  - YouTube : 1920x1080 (16:9)
  - Short : 1080x1920 (9:16)
  - Instagram : 1080x1080 (1:1)

### Étape 6 : Preview et render

```bash
# Preview dans le browser
npm run dev

# Render MP4
npx remotion render <CompositionId> output.mp4 --codec h264
```

## Patterns de texte accrocheur (style ANAKIN)

Pour les hooks et titres, utiliser ce ton :
```yaml
hooks:
  - "J'ai automatisé [X] avec Claude Code..."
  - "Ce truc a changé ma façon de coder"
  - "[X] en [temps] — voici comment"
  - "Le setup que personne montre"
  - "J'ai codé [X] de zéro — devlog #N"

titres_chapitres:
  - "LE PROBLÈME"
  - "LA SOLUTION"  
  - "LE CODE"
  - "LE RÉSULTAT"
  - "COMMENT ÇA MARCHE"

cta:
  - "Abonne-toi pour le prochain devlog"
  - "Like si t'as appris un truc"
  - "Commente ton [X] préféré"
```

## Exemples de prompts

### Devlog
```
Crée un devlog de 2 minutes sur mon projet Roblox.
Assets : 4 screenshots dans assets/screens/
Chapitres : "L'idée", "Le code", "Le résultat"
```

### Short
```
Short vertical de 30s : "3 commandes Claude Code que personne connaît"
3 commandes avec démo code rapide, transitions punchy
```

### Intro
```
Crée une intro YouTube de 5 secondes pour ma chaîne ANAKIN
Avec mon logo (assets/logo.png), animation énergique, son whoosh
```

### Showcase
```
Showcase de mon MCP server Roblox, 3 minutes
Montre : setup, démo live, features principales
Screenshots dans assets/
```

## Composants réutilisables à toujours avoir

| Composant | Usage |
|-----------|-------|
| `AnakinIntro.tsx` | Intro de chaîne avec logo animé |
| `AnakinOutro.tsx` | Outro avec CTA et liens |
| `ChapterTitle.tsx` | Titre de chapitre numéroté |
| `CodeBlock.tsx` | Code avec syntax highlighting |
| `TextReveal.tsx` | Texte qui apparaît avec animation |
| `ProgressBar.tsx` | Barre de progression en haut |
| `Watermark.tsx` | Watermark ANAKIN semi-transparent |
| `ParticleBackground.tsx` | Fond avec particules animées |
| `GlowText.tsx` | Texte avec halo lumineux |
| `FeatureCard.tsx` | Carte feature avec icône + description |

## Résolutions et formats

```typescript
const FORMATS = {
  youtube: { width: 1920, height: 1080, fps: 30 },
  youtube4k: { width: 3840, height: 2160, fps: 30 },
  short: { width: 1080, height: 1920, fps: 30 },
  instagram: { width: 1080, height: 1080, fps: 30 },
  thumbnail: { width: 1280, height: 720, fps: 1 },
};
```

## Règles absolues

1. **TOUJOURS** utiliser la palette ANAKIN_COLORS — jamais de couleurs génériques
2. **TOUJOURS** mettre le watermark ANAKIN en bas à droite
3. **TOUJOURS** commencer par un hook dans les 3 premières secondes
4. **TOUJOURS** utiliser des spring animations, jamais de linear/ease
5. **TOUJOURS** inclure un CTA à la fin (subscribe, like, comment)
6. **JAMAIS** de fond blanc uni — toujours le gradient sombre ANAKIN
7. **JAMAIS** de texte petit — minimum 48px pour les titres, 32px pour le corps
8. **JAMAIS** de silence visuel — toujours quelque chose qui bouge
9. **FRANÇAIS** par défaut pour tout le texte
10. **ÉNERGIE** — le rythme doit être rapide, pas de moments morts
