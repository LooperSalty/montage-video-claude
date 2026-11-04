import { Html5Audio, interpolate, Sequence, staticFile, useVideoConfig } from 'remotion';
import { msToFrame } from '../theme';
import type { Sfx, Timeline } from '../types';

const clamp = { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' } as const;
const SFX_MAX_FRAMES = 120;
const STAMP_SFX = 'sfx/stamp.mp3';
const OUTRO_SFX = 'sfx/hit.mp3';
const OUTRO_MUSIC_BOOST = 2.2; // plus de voix pendant l'outro : la musique remonte

const collectSfx = (timeline: Timeline): Sfx[] => {
  const beatSfx = timeline.beats.flatMap((b) => b.sfx);
  const stampSfx = timeline.beats
    .filter((b) => b.stamp !== null)
    .map((b) => ({ src: STAMP_SFX, atMs: b.stamp!.atMs, volume: 0.5 }));
  const outro = { src: OUTRO_SFX, atMs: timeline.outro.startMs, volume: 0.55 };
  return [...beatSfx, ...stampSfx, outro];
};

export const AudioLayer: React.FC<{ timeline: Timeline }> = ({ timeline }) => {
  const { fps, durationInFrames } = useVideoConfig();
  const outroFrame = msToFrame(timeline.outro.startMs, fps);
  const musicVolume = (f: number): number => {
    const fade = interpolate(f, [0, 15, durationInFrames - 20, durationInFrames], [0, 1, 1, 0], clamp);
    const boost = interpolate(f, [outroFrame, outroFrame + 10], [1, OUTRO_MUSIC_BOOST], clamp);
    return timeline.music.volume * fade * boost;
  };
  return (
    <>
      <Html5Audio src={staticFile(timeline.voice)} />
      <Html5Audio src={staticFile(timeline.music.src)} loop volume={musicVolume} />
      {collectSfx(timeline).map((s, k) => (
        <Sequence key={`${s.src}-${s.atMs}-${k}`} from={msToFrame(s.atMs, fps)} durationInFrames={SFX_MAX_FRAMES} layout="none">
          <Html5Audio src={staticFile(s.src)} volume={s.volume} />
        </Sequence>
      ))}
    </>
  );
};
