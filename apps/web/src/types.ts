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

export type Transcriber = "basic_pitch" | "crepe";

export const TRANSCRIBERS: { id: Transcriber; label: string; hint: string }[] = [
  {
    id: "basic_pitch",
    label: "Basic Pitch",
    hint: "다성부용. 노이즈에 강하지만 하모닉을 별개 노트로 검출하는 경향 있음",
  },
  {
    id: "crepe",
    label: "CREPE",
    hint: "단성부 전용. 깨끗한 베이스 라인엔 더 정확하지만 분리 잔여 노이즈에 약함",
  },
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
