export type Note = {
  pitch: number;
  start: number;
  duration: number;
  velocity: number;
};

export type TabNote = {
  string: number;
  fret: number;
  start: number;
  duration: number;
  pitch: number;
};

export type TranscribeResult = {
  job_id: string;
  notes: Note[];
  tab: TabNote[];
  musicxml_url: string;
  midi_url: string;
  tuning: string;
  transcriber: string;
};
