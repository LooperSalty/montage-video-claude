// Contrat de données produit par pipeline/build_story.py (timeline.json).

export type Word = { text: string; startMs: number; endMs: number };

export type BeatImage = { src: string; bg: string; w: number; h: number };

export type Sfx = { src: string; atMs: number; volume: number };

export type Grade = 'archive' | 'natural';

export type Beat = {
  i: number;
  startMs: number;
  endMs: number;
  img: BeatImage;
  mode: 'cover' | 'card';
  focus: [number, number];
  label?: string | null;
  grade: Grade;
  stamp: { text: string; atMs: number } | null;
  sfx: Sfx[];
  words: Word[];
};

export type Timeline = {
  id: string;
  episode: number;
  title: string;
  fps: number;
  durationMs: number;
  grade: Grade;
  hook: { lines: string[]; endMs: number };
  music: { src: string; volume: number };
  voice: string;
  outro: { startMs: number; text: string };
  beats: Beat[];
};

export type StoryProps = { storyId: string; timeline: Timeline | null };
