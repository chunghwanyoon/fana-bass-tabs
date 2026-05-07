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

export type TimeSignature =
  | "4/4"
  | "3/4"
  | "6/8"
  | "2/4"
  | "5/4"
  | "7/8"
  | "12/8";

export const TIME_SIGNATURES: TimeSignature[] = [
  "4/4",
  "3/4",
  "6/8",
  "2/4",
  "5/4",
  "7/8",
  "12/8",
];

export type TranscribeResult = {
  job_id: string;
  notes: Note[];
  tab: TabNote[];
  musicxml_url: string;
  midi_url: string;
  tuning: string;
  transcriber: string;
  bpm: number;
  title: string;
  time_signature: string;
};

export type JobAccepted = {
  job_id: string;
  status: "queued";
};

export type JobStatus = "queued" | "running" | "complete" | "failed" | "not_found";

export type JobStatusResponse = {
  job_id: string;
  status: JobStatus;
  stage: string | null;
  stage_progress: number | null;
  result: TranscribeResult | null;
  error: string | null;
};
