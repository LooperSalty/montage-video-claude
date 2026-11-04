import { interpolate, spring, useCurrentFrame, useVideoConfig } from 'remotion';
import { COLORS, FONT, LAYOUT } from '../theme';

type Props = { text: string; index: number; durationFrames: number; top?: number; maxFont?: number };

const clamp = { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' } as const;

// Tampon rouge d'archive qui « claque » à l'écran sur un mot-clé.
export const Stamp: React.FC<Props> = ({ text, index, durationFrames, top = LAYOUT.stampY, maxFont = 118 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const slam = spring({ frame, fps, config: { damping: 11, stiffness: 260, mass: 0.7 } });
  const scale = interpolate(slam, [0, 1], [2.4, 1]);
  const fadeIn = interpolate(frame, [0, 3], [0, 1], clamp);
  const fadeOut = interpolate(frame, [durationFrames - 6, durationFrames], [1, 0], clamp);
  const shake = frame < 9 ? Math.sin(frame * 2.6) * (9 - frame) * 1.3 : 0;
  const tilt = index % 2 === 0 ? -6 : 5;
  const fontSize = Math.min(maxFont, Math.floor(1300 / Math.max(6, text.length)));
  return (
    <div
      style={{
        position: 'absolute', top, left: '50%', opacity: fadeIn * fadeOut,
        transform: `translate(-50%, -50%) translateX(${shake}px) rotate(${tilt}deg) scale(${scale})`,
        border: `8px solid ${COLORS.red}`, outline: `3px solid ${COLORS.red}`, outlineOffset: 7,
        padding: '8px 30px', color: COLORS.red, background: 'rgba(243,233,210,0.93)',
        fontFamily: FONT, fontWeight: 900, fontSize, letterSpacing: 2, whiteSpace: 'nowrap',
        textTransform: 'uppercase', boxShadow: '0 14px 44px rgba(0,0,0,0.55)',
      }}
    >
      {text}
    </div>
  );
};
