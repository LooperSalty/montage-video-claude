import { AbsoluteFill, interpolate, random, spring, staticFile, useCurrentFrame, useVideoConfig } from 'remotion';
import { COLORS, FONT, LAYOUT, MONO } from '../theme';

const clamp = { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' } as const;

// Grain argentique + vignette : donne le look « archive » à toutes les images.
export const FilmLook: React.FC = () => {
  const frame = useCurrentFrame();
  const x = Math.floor(random(`gx-${frame}`) * 512);
  const y = Math.floor(random(`gy-${frame}`) * 512);
  return (
    <>
      <AbsoluteFill
        style={{
          backgroundImage: `url(${staticFile('fx/grain.png')})`, backgroundPosition: `${x}px ${y}px`,
          mixBlendMode: 'overlay', opacity: 0.16,
        }}
      />
      <AbsoluteFill style={{ background: 'radial-gradient(ellipse at 50% 45%, rgba(0,0,0,0) 55%, rgba(0,0,0,0.55) 100%)' }} />
    </>
  );
};

export const ProgressBar: React.FC = () => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  return (
    <div
      style={{
        position: 'absolute', top: 0, left: 0, height: 10, width: `${(frame / durationInFrames) * 100}%`,
        background: COLORS.accent, boxShadow: '0 0 18px rgba(255,210,31,0.7)',
      }}
    />
  );
};

export const EpisodeTag: React.FC<{ episode: number }> = ({ episode }) => (
  <div
    style={{
      position: 'absolute', top: 200, left: 48, padding: '6px 14px', background: 'rgba(11,11,15,0.6)',
      border: `2px solid ${COLORS.accent}`, color: COLORS.paper, fontFamily: MONO, fontWeight: 700,
      fontSize: 26, letterSpacing: 2,
    }}
  >
    DOSSIER Nº{String(episode).padStart(3, '0')}
  </div>
);

export const HookTitle: React.FC<{ lines: string[]; durationFrames: number }> = ({ lines, durationFrames }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const exit = interpolate(frame, [durationFrames - 7, durationFrames], [0, 1], clamp);
  return (
    <div style={{ position: 'absolute', top: LAYOUT.hookTop, left: 0, right: 0, textAlign: 'center', opacity: 1 - exit }}>
      {lines.map((line, k) => {
        const s = spring({ frame: frame - k * 4, fps, config: { damping: 14, stiffness: 200 } });
        const fontSize = Math.min(110, Math.floor(1250 / Math.max(6, line.length)));
        return (
          <div key={line} style={{ margin: '8px 0' }}>
            <span
              style={{
                display: 'inline-block', background: k === 0 ? COLORS.accent : COLORS.white, color: COLORS.ink,
                fontFamily: FONT, fontWeight: 900, fontSize, padding: '2px 24px', lineHeight: 1.15,
                transform: `translateX(${(1 - s) * (k % 2 === 0 ? -1100 : 1100)}px) rotate(-2deg) translateY(${-exit * 40}px)`,
                boxShadow: '0 12px 34px rgba(0,0,0,0.55)',
              }}
            >
              {line}
            </span>
          </div>
        );
      })}
    </div>
  );
};
