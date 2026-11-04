import { AbsoluteFill, Easing, Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from 'remotion';
import { COLORS, GRADES, LAYOUT, MAX_COVER_UPSCALE } from '../theme';
import type { Beat } from '../types';
import { TapeLabel } from './TapeLabel';

type Props = { beat: Beat; index: number; durationFrames: number; transitionFrames: number };

const clamp = { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' } as const;
const CARD_BORDER = 16;

const coverUpscale = (w: number, h: number): number => Math.max(LAYOUT.width / w, LAYOUT.height / h);

const cardSize = (w: number, h: number): { cw: number; ch: number } => {
  const ratio = w / h;
  const byWidth = { cw: LAYOUT.cardMaxW, ch: LAYOUT.cardMaxW / ratio };
  return byWidth.ch <= LAYOUT.cardMaxH ? byWidth : { cw: LAYOUT.cardMaxH * ratio, ch: LAYOUT.cardMaxH };
};

const CoverShot: React.FC<Props & { punch: number }> = ({ beat, index, durationFrames, punch }) => {
  const frame = useCurrentFrame();
  const progress = Math.min(1, frame / Math.max(1, durationFrames));
  const zoomIn = index % 2 === 0;
  const scale = (zoomIn ? 1.06 + 0.12 * progress : 1.18 - 0.12 * progress) * punch;
  const [fx, fy] = beat.focus;
  const origin = `${fx * 100}% ${fy * 100}%`;
  return (
    <>
      <Img
        src={staticFile(beat.img.src)}
        style={{
          width: '100%', height: '100%', objectFit: 'cover', objectPosition: origin,
          transform: `scale(${scale})`, transformOrigin: origin, filter: GRADES[beat.grade],
        }}
      />
      <AbsoluteFill
        style={{
          background:
            'linear-gradient(180deg, rgba(0,0,0,0.45) 0%, rgba(0,0,0,0) 22%, rgba(0,0,0,0) 45%, rgba(0,0,0,0.55) 68%, rgba(0,0,0,0.8) 100%)',
        }}
      />
      {beat.label ? <TapeLabel text={beat.label} top={LAYOUT.coverLabelTop} tilt={-1.5} /> : null}
    </>
  );
};

const CardShot: React.FC<Props & { punch: number }> = ({ beat, index, durationFrames, punch }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const progress = Math.min(1, frame / Math.max(1, durationFrames));
  const enter = spring({ frame, fps, config: { damping: 15, stiffness: 140, mass: 0.8 } });
  const { cw, ch } = cardSize(beat.img.w, beat.img.h);
  const baseTilt = index % 2 === 0 ? -1.6 : 1.4;
  const tilt = baseTilt + (1 - enter) * baseTilt * 2;
  const lift = interpolate(enter, [0, 1], [90, 0]);
  const top = LAYOUT.cardCenterY - ch / 2 - CARD_BORDER;
  return (
    <>
      <Img
        src={staticFile(beat.img.bg)}
        style={{ width: '100%', height: '100%', objectFit: 'cover', transform: `scale(${1.08 + 0.06 * progress})` }}
      />
      <div
        style={{
          position: 'absolute', left: (LAYOUT.width - cw) / 2 - CARD_BORDER, top: top + lift,
          width: cw, height: ch, padding: CARD_BORDER, background: COLORS.paper,
          boxShadow: '0 40px 90px rgba(0,0,0,0.75)',
          transform: `rotate(${tilt}deg) scale(${(0.9 + 0.1 * enter) * punch})`,
        }}
      >
        <div style={{ width: '100%', height: '100%', overflow: 'hidden' }}>
          <Img
            src={staticFile(beat.img.src)}
            style={{
              width: '100%', height: '100%', objectFit: 'cover',
              transform: `scale(${1.0 + 0.07 * progress})`, filter: GRADES[beat.grade],
            }}
          />
        </div>
      </div>
      {beat.label ? (
        <TapeLabel text={beat.label} top={top + ch + 2 * CARD_BORDER + 26 + lift} tilt={-baseTilt} />
      ) : null}
    </>
  );
};

export const Visual: React.FC<Props> = (props) => {
  const frame = useCurrentFrame();
  const { transitionFrames, beat } = props;
  const opacity = transitionFrames > 0 ? interpolate(frame, [0, transitionFrames], [0, 1], clamp) : 1;
  const punch = interpolate(frame, [0, transitionFrames + 8], [1.07, 1], { ...clamp, easing: Easing.out(Easing.cubic) });
  const tooSmall = coverUpscale(beat.img.w, beat.img.h) > MAX_COVER_UPSCALE;
  const Shot = beat.mode === 'card' || tooSmall ? CardShot : CoverShot;
  return (
    <AbsoluteFill style={{ opacity, overflow: 'hidden', backgroundColor: COLORS.ink }}>
      <Shot {...props} punch={punch} />
    </AbsoluteFill>
  );
};
