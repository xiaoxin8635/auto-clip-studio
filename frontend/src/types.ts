export interface Segment {
  id: string;
  title: string;
  rationale: string;
  start_ms: number;
  end_ms: number;
  caption_text: string;
  status: string;
  download_url?: string | null;
}

export interface Project {
  id: string;
  status: string;
  source_filename?: string | null;
  duration_ms: number;
  transcript_text: string;
  error_message?: string | null;
  segments: Segment[];
}
