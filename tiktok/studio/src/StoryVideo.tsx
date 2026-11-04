import { AbsoluteFill, Sequence, useVideoConfig } from 'remotion';
import { AudioLayer } from './components/AudioLayer';
import { Captions } from './components/Captions';
import { Outro } from './components/Outro';
import { EpisodeTag, FilmLook, HookTitle, ProgressBar } from './components/Overlays';
import { Stamp } from './components/Stamp';
import { Visual } from './components/Visual';
import { COLORS, msToFrame, TRANSITION_FRAMES } from './theme';
import type { StoryProps } from './types';

const HANDLE = '@pourtant.cest.vrai';
const STAMP_MAX_S = 2.4;

export const StoryVideo: React.FC<StoryProps> = ({ timeline }) => {
  const { fps, durationInFrames } = useVideoConfig();
  if (!timeline) return <AbsoluteFill style={{ backgroundColor: COLORS.ink }} />;
  const f = (ms: number): number => msToFrame(ms, fps);
  const lastIdx = timeline.beats.length - 1;
  const outroFrom = f(timeline.outro.startMs);

  return (
    <AbsoluteFill style={{ backgroundColor: COLORS.ink }}>
      {timeline.beats.map((beat, idx) => {
        const transition = idx === 0 ? 0 : TRANSITION_FRAMES;
        const from = Math.max(0, f(beat.startMs) - transition);
        const until = idx === lastIdx ? durationInFrames : f(beat.endMs) + 1;
        return (
          <Sequence key={beat.i} from={from} durationInFrames={Math.max(1, until - from)}>
            <Visual beat={beat} index={idx} durationFrames={until - from} transitionFrames={transition} />
          </Sequence>
        );
      })}

      <FilmLook />

      {timeline.beats.map((beat, idx) => {
        if (!beat.stamp) return null;
        const from = f(beat.stamp.atMs);
        const limit = idx === lastIdx ? outroFrom : f(beat.endMs) + 6;
        const dur = Math.max(8, Math.min(limit - from, Math.round(STAMP_MAX_S * fps)));
        return (
          <Sequence key={`stamp-${beat.i}`} from={from} durationInFrames={dur} layout="none">
            <Stamp text={beat.stamp.text} index={idx} durationFrames={dur} />
          </Sequence>
        );
      })}

      <Captions beats={timeline.beats} />

      <Sequence durationInFrames={Math.max(1, f(timeline.hook.endMs))} layout="none">
        <HookTitle lines={timeline.hook.lines} durationFrames={f(timeline.hook.endMs)} />
      </Sequence>

      <EpisodeTag episode={timeline.episode} />
      <ProgressBar />

      <Sequence from={outroFrom} durationInFrames={Math.max(1, durationInFrames - outroFrom)}>
        <Outro text={timeline.outro.text} durationFrames={durationInFrames - outroFrom} handle={HANDLE} />
      </Sequence>

      <AudioLayer timeline={timeline} />
    </AbsoluteFill>
  );
};
