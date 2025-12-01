// User types
export interface User {
  id: string;
  email: string;
  name: string;
  avatar_url?: string;
  google_sub: string;
  created_at: string;
  updated_at: string;
}

// Video types
export interface Video {
  id: string;
  user_id: string;
  youtube_video_id: string;
  original_url: string;
  title?: string;
  thumbnail_url?: string;
  duration_seconds?: number;
  status: 'PENDING' | 'PROCESSING' | 'READY' | 'FAILED';
  failure_reason?: string;
  processed_at?: string;
  created_at: string;
  updated_at: string;
}

// Job types
export interface Job {
  id: string;
  video_id: string;
  type: 'VIDEO_PROCESS' | 'PDF_EXPORT';
  status: 'PENDING' | 'FETCHING_TRANSCRIPT' | 'GENERATING_NOTES' | 'COMPLETED' | 'FAILED';
  progress: number;
  error_message?: string;
  created_at: string;
  started_at?: string;
  completed_at?: string;
}

// Notes types
export interface Timestamp {
  label: string;
  time: string;
  seconds: number;
}

export interface Flashcard {
  front: string;
  back: string;
}

export interface Chapter {
  title: string;
  start_time: number;
  end_time: number;
  summary?: string;
}

export interface Notes {
  summary: string;
  bullets: string[];
  key_timestamps: Timestamp[];
  flashcards: Flashcard[];
  action_items: string[];
  difficulty_level?: 'beginner' | 'intermediate' | 'advanced';
  topics?: string[];
  markdown_notes?: string;
  chapters?: Chapter[];
  suggested_prompts?: string[];
}

export interface TranscriptSegment {
  text: string;
  start: number;
  duration: number;
}

export interface Transcript {
  language_code: string;
  provider: string;
  raw_text: string;
  segments: TranscriptSegment[];
}

// Video with full details
export interface VideoDetail extends Video {
  notes?: Notes;
  transcript?: Transcript;
}

// API response types for video endpoints
export interface VideoCreateResponse {
  video: Video;
  job_id: string;
  message: string;
}

export interface VideoListResponse {
  videos: Video[];
  total: number;
}

export interface VideoStatusResponse {
  video: Video;
  jobs: Job[];
}

// Quiz types
export interface QuizQuestion {
  id: string;
  video_id: string;
  question_text: string;
  question_type: 'MCQ' | 'TRUE_FALSE' | 'SHORT';
  options?: string[];
  correct_option_index?: number;
  correct_answer?: string;
  explanation?: string;
  related_timestamp_seconds?: number;
  concept_tag?: string;
  difficulty?: 'easy' | 'medium' | 'hard';
}

export interface QuizSession {
  id: string;
  user_id: string;
  video_id: string;
  score?: number;
  total_questions?: number;
  started_at: string;
  completed_at?: string;
  questions: QuizQuestion[];
}

export interface QuizAnswer {
  question_id: string;
  selected_option_index?: number;
  submitted_answer?: string;
}

export interface QuizResult {
  score: number;
  total_questions: number;
  results: {
    question_id: string;
    is_correct: boolean;
    explanation?: string;
    related_timestamp_seconds?: number;
  }[];
}

// Chat types
export interface ChatMessage {
  id: string;
  user_id: string;
  video_id: string;
  role: 'user' | 'assistant';
  message_type: 'chat' | 'teach_back' | 'system';
  content: string;
  metadata?: {
    related_timestamp_seconds?: number;
  };
  created_at: string;
}

// Export types
export interface Export {
  id: string;
  user_id: string;
  video_id: string;
  export_type: 'PDF' | 'MARKDOWN';
  file_url?: string;
  file_size_bytes?: number;
  status: 'PENDING' | 'READY' | 'FAILED';
  created_at: string;
  completed_at?: string;
}

// API Response types
export interface ApiResponse<T> {
  data: T;
  message?: string;
}

export interface ApiError {
  detail: string;
}

// Seek / "Take Me There" types
export interface SeekResponse {
  timestamp: number | null;
  confidence: 'high' | 'medium' | 'low' | 'none';
  matched_text: string;
}

// User Notes types
export interface UserNote {
  id: string;
  text: string;
  timestamp: number;
  created_at: string;
  rewritten_text: string | null;
}

export type RewriteStyle = 'simplify' | 'summarize' | 'formal' | 'bullet_points' | 'explain';

export interface RewriteStyleOption {
  value: RewriteStyle;
  label: string;
  description: string;
}

export const REWRITE_STYLES: RewriteStyleOption[] = [
  { value: 'simplify', label: 'Simplify', description: 'Easier to understand language' },
  { value: 'summarize', label: 'Summarize', description: 'Condense into 1-2 sentences' },
  { value: 'formal', label: 'Formal', description: 'Professional language' },
  { value: 'bullet_points', label: 'Bullet Points', description: 'Convert to bullet list' },
  { value: 'explain', label: 'Explain', description: 'Explain for beginners' },
];
