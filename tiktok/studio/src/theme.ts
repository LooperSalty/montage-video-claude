// Charte « Pourtant c'est vrai » : dossier d'archives, surligneur jaune, tampon rouge.
import type { Grade } from './types';

export const COLORS = {
  ink: '#0B0B0F',
  paper: '#F3E9D2',
  accent: '#FFD21F',
  red: '#D62828',
  white: '#FFFFFF',
} as const;

export const FONT = 'Montserrat, Arial Black, sans-serif';
export const MONO = '"Courier New", Courier, monospace';

export const GRADES: Record<Grade, string> = {
  archive: 'grayscale(0.25) sepia(0.35) contrast(1.08) brightness(0.96)',
  natural: 'saturate(1.08) contrast(1.06)',
};

// Zones sûres TikTok (1080x1920) : on évite le haut (onglets), le bas (légende) et la droite (boutons).
export const LAYOUT = {
  width: 1080,
  height: 1920,
  hookTop: 300,
  cardCenterY: 620,
  cardMaxW: 900,
  cardMaxH: 820,
  coverLabelTop: 1060,
  stampY: 900,
  captionY: 1270,
  sideMargin: 80,
} as const;

export const TRANSITION_FRAMES = 6;
export const MAX_COVER_UPSCALE = 2.2; // au-delà, l'image est trop petite : on passe en mode carte

export const msToFrame = (ms: number, fps: number): number => Math.round((ms / 1000) * fps);

// Contour noir épais façon sous-titres TikTok, robuste dans Chrome headless.
export const outline = (px: number, color = '#000'): string => {
  const steps = 16;
  const rings = Array.from({ length: steps }, (_, k) => {
    const a = (2 * Math.PI * k) / steps;
    return `${(Math.cos(a) * px).toFixed(1)}px ${(Math.sin(a) * px).toFixed(1)}px 0 ${color}`;
  });
  return [...rings, '0 10px 28px rgba(0,0,0,0.65)'].join(', ');
};
