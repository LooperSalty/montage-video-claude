import { CalculateMetadataFunction, Composition, staticFile } from 'remotion';
import { StoryVideo } from './StoryVideo';
import type { StoryProps, Timeline } from './types';
import './fonts';

// Ajouter ici l'id de chaque nouvelle histoire (= nom du fichier stories/<id>.json).
const STORIES = ['lustig', 'jessop', 'emeus'] as const;
const FPS = 30;

const calculateMetadata: CalculateMetadataFunction<StoryProps> = async ({ props }) => {
  const res = await fetch(staticFile(`stories/${props.storyId}/timeline.json`));
  if (!res.ok) {
    throw new Error(`timeline.json introuvable pour « ${props.storyId} » : lancer pipeline/build_story.py`);
  }
  const timeline = (await res.json()) as Timeline;
  return {
    durationInFrames: Math.ceil((timeline.durationMs / 1000) * FPS),
    props: { ...props, timeline },
  };
};

export const RemotionRoot: React.FC = () => (
  <>
    {STORIES.map((id) => (
      <Composition
        key={id}
        id={id}
        component={StoryVideo}
        width={1080}
        height={1920}
        fps={FPS}
        durationInFrames={60 * FPS}
        defaultProps={{ storyId: id, timeline: null }}
        calculateMetadata={calculateMetadata}
      />
    ))}
  </>
);
