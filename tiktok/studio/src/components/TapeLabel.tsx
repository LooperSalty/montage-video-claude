import { useCurrentFrame } from 'remotion';
import { COLORS, MONO } from '../theme';

type Props = { text: string; top: number; tilt: number; delayFrames?: number };

const CHARS_PER_FRAME = 1.6;

// Étiquette d'archive tapée à la machine sur un morceau de scotch.
export const TapeLabel: React.FC<Props> = ({ text, top, tilt, delayFrames = 8 }) => {
  const frame = useCurrentFrame();
  const visible = Math.max(0, Math.floor((frame - delayFrames) * CHARS_PER_FRAME));
  if (visible === 0) return null;
  const typed = text.slice(0, visible);
  return (
    <div
      style={{
        position: 'absolute', left: '50%', top, transform: `translateX(-50%) rotate(${tilt}deg)`,
        background: 'rgba(243,233,210,0.94)', color: COLORS.ink, fontFamily: MONO, fontWeight: 700,
        fontSize: 30, letterSpacing: 2, padding: '8px 22px', whiteSpace: 'nowrap',
        boxShadow: '0 8px 24px rgba(0,0,0,0.45)', maxWidth: 940, overflow: 'hidden',
      }}
    >
      {typed}
      <span style={{ opacity: visible < text.length ? 1 : 0 }}>▌</span>
    </div>
  );
};
