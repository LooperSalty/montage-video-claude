import { useMemo } from 'react';
import { spring, useCurrentFrame, useVideoConfig } from 'remotion';
import { COLORS, FONT, LAYOUT, msToFrame, outline } from '../theme';
import type { Beat, Word } from '../types';

type Page = { startMs: number; endMs: number; words: Word[] };

const MAX_WORDS = 3;
const MAX_CHARS = 18;
const PAUSE_BREAK_MS = 220; // une pause dans la voix = fin de groupe de mots
const LINGER_MS = 350;
const TEXT_SHADOW = outline(6);

const chars = (words: Word[]): number => words.reduce((n, w) => n + w.text.length + 1, 0);

export const buildPages = (beats: Beat[]): Page[] => {
  const groups: Word[][] = [];
  beats.forEach((beat) => {
    let current: Word[] = [];
    beat.words.forEach((w) => {
      const prev = current[current.length - 1];
      const full = current.length >= MAX_WORDS || chars(current) + w.text.length > MAX_CHARS;
      const paused = prev !== undefined && w.startMs - prev.endMs > PAUSE_BREAK_MS;
      if (current.length > 0 && (full || paused)) {
        groups.push(current);
        current = [];
      }
      current = [...current, w];
    });
    if (current.length > 0) groups.push(current);
  });
  return groups.map((words, k) => {
    const last = words[words.length - 1];
    const next = groups[k + 1]?.[0];
    const endMs = Math.min(next ? next.startMs : Infinity, last.endMs + LINGER_MS);
    return { startMs: words[0].startMs, endMs, words };
  });
};

export const Captions: React.FC<{ beats: Beat[] }> = ({ beats }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const pages = useMemo(() => buildPages(beats), [beats]);
  const t = (frame / fps) * 1000;
  const page = pages.find((p) => t >= p.startMs && t < p.endMs);
  if (!page) return null;

  const pop = spring({ frame: frame - msToFrame(page.startMs, fps), fps, config: { damping: 12, stiffness: 240, mass: 0.6 } });
  const activeIdx = page.words.reduce((acc, w, k) => (t >= w.startMs ? k : acc), 0);

  return (
    <div
      style={{
        position: 'absolute', top: LAYOUT.captionY, left: LAYOUT.sideMargin, right: LAYOUT.sideMargin,
        transform: `translateY(-50%) scale(${0.82 + 0.18 * pop})`, textAlign: 'center',
        fontFamily: FONT, fontWeight: 900, fontSize: 84, lineHeight: 1.12, textTransform: 'uppercase',
        color: COLORS.white, textShadow: TEXT_SHADOW,
      }}
    >
      {page.words.map((w, k) => (
        <span key={`${w.startMs}-${k}`}>
          {k > 0 ? ' ' : null}
          <span
            style={{
              display: 'inline-block', margin: '0 6px',
              color: k === activeIdx ? COLORS.accent : COLORS.white,
              transform: k === activeIdx ? 'scale(1.06)' : 'none',
            }}
          >
            {w.text}
          </span>
        </span>
      ))}
    </div>
  );
};
