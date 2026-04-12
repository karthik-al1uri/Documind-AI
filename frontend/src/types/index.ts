/**
 * TypeScript type definitions for the DocuMind AI frontend.
 * Mirrors the Pydantic schemas defined in backend/models/schemas.py.
 */

export interface BoundingBox {
  x0: number;
  y0: number;
  x1: number;
  y1: number;
}

export interface RetrievalResult {
  chunk_id: string;
  document_id: string;
  text: string;
  score: number;
  page_number: number;
  section_heading: string | null;
  bbox: BoundingBox | null;
  source_filename: string;
}

export interface Claim {
  text: string;
  confidence: number;
  entailment_label: string | null;
  entailment_score: number | null;
  citation?: {
    chunk_id: string;
    document_id: string;
    page_number: number;
    source_filename: string;
  };
}

export interface AnswerResponse {
  answer: string;
  claims: Claim[];
  sources: RetrievalResult[];
  query_id: string;
}

export interface DocumentInfo {
  id: string;
  filename: string;
  file_type: string;
  doc_type: string | null;
  language: string;
  status: string;
  upload_date: string;
  metadata: Record<string, unknown>;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  answer_response?: AnswerResponse;
  status?: 'sending' | 'streaming' | 'complete' | 'error';
}

export interface SSEEvent {
  type: 'status' | 'token' | 'answer' | 'done' | 'error';
  stage?: string;
  text?: string;
  data?: AnswerResponse;
  message?: string;
  query_id?: string;
}
