# anakin-video-creator

Skill Claude Code personnalisée pour créer des vidéos YouTube avec [Remotion](https://www.remotion.dev/) — adaptée au style et branding d'ANAKIN.

## Fonctionnalités

- **Charte graphique intégrée** — palette de couleurs, typographie, animations signature
- **3 templates de vidéo** — Devlog, Short/Reel, Showcase
- **10 composants réutilisables** — Intro, Outro, ChapterTitle, CodeBlock, TextReveal, ProgressBar, Watermark, ParticleBackground, GlowText, FeatureCard
- **Hooks et textes accrocheurs** — ton direct et énergique en français
- **Multi-format** — YouTube 16:9, Shorts 9:16, Instagram 1:1

## Style visuel

| Élément | Valeur |
|---------|--------|
| Couleur principale | `#FF6B35` (Orange vif) |
| Couleur secondaire | `#004E98` (Bleu profond) |
| Accent | `#FFD23F` (Jaune doré) |
| Fond | `#0A0A0F` → `#16213E` (gradient) |
| Police titres | Inter Black, uppercase |
| Police code | JetBrains Mono |
| Animations | Spring-based (damping: 12, stiffness: 200) |

## Prérequis

- [Node.js](https://nodejs.org/) 18+
- [Remotion](https://www.remotion.dev/) (`npm create video@latest`)
- [Claude Code](https://claude.ai) avec cette skill installée

## Installation

```bash
# Copier dans le dossier skills Claude Code
cp -r anakin-video-creator ~/.claude/skills/
```

Ou cloner directement :
```bash
git clone git@github.com:LooperSalty/anakin-video-creator.git ~/.claude/skills/anakin-video-creator
```

## Utilisation

Demander à Claude Code de créer une vidéo — la skill s'active automatiquement :

```
Crée un devlog de 2 minutes sur mon projet Roblox MCP
```

```
Short vertical : "3 commandes Claude Code que personne connaît"
```

```
Showcase de mon app avec les screenshots dans assets/
```

## Templates disponibles

### 1. Devlog (10-30 min)
Structure : Hook → Intro animée → Chapitres → Code highlights → Outro CTA

### 2. Short / Reel (< 60s, vertical)
Structure : Hook texte impact → Contenu rapide → Résultat → CTA

### 3. Showcase (3-5 min)
Structure : Teaser → Intro → Walkthrough features → Outro

## Composants

| Composant | Description |
|-----------|-------------|
| `AnakinIntro.tsx` | Intro de chaîne avec logo animé |
| `AnakinOutro.tsx` | Outro avec CTA et liens |
| `ChapterTitle.tsx` | Titre de chapitre numéroté |
| `CodeBlock.tsx` | Code avec syntax highlighting animé |
| `TextReveal.tsx` | Texte avec animation d'apparition |
| `ProgressBar.tsx` | Barre de progression en haut |
| `Watermark.tsx` | Watermark ANAKIN semi-transparent |
| `ParticleBackground.tsx` | Fond avec particules animées |
| `GlowText.tsx` | Texte avec halo lumineux |
| `FeatureCard.tsx` | Carte feature avec icône + description |

## Licence

Usage personnel — ANAKIN / LooperSalty
