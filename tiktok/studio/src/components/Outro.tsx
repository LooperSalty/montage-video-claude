import { AbsoluteFill, interpolate, useCurrentFrame } from 'remotion';
import { COLORS, MONO } from '../theme';
import { Stamp } from './Stamp';

type Props = { text: string; durationFrames: number; handle: string };

const clamp = { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' } as const;

// Signature de fin : assombrit l'image et claque le tampon de la chaîne.
export const Outro: React.FC<Props> = ({ text, durationFrames, handle }) => {
  const frame = useCurrentFrame();
  const dim = interpolate(frame, [0, 8], [0, 0.62], clamp);
  const sub = interpolate(frame, [10, 18], [0, 1], clamp);
  return (
    <AbsoluteFill>
      <AbsoluteFill style={{ backgroundColor: `rgba(11,11,15,${dim})` }} />
      <Stamp text={text} index={0} durationFrames={durationFrames + 30} top={860} maxFont={96} />
      <div
        style={{
          position: 'absolute', top: 1010, left: 0, right: 0, textAlign: 'center', opacity: sub,
          color: COLORS.paper, fontFamily: MONO, fontWeight: 700, fontSize: 38, letterSpacing: 3,
        }}
      >
        {handle}
        <div style={{ fontSize: 28, marginTop: 14, color: COLORS.accent }}>UNE HISTOIRE VRAIE PAR JOUR</div>
      </div>
    </AbsoluteFill>
  );
};
