/**
 * API client for DocuMind AI backend.
 * Uses NEXT_PUBLIC_API_URL when set (e.g. http://localhost:8002), else same-origin /api (Next rewrites).
 */

import { AnswerResponse, CompareResponse, DocumentInfo, SSEEvent } from '@/types';

function apiBase(): string {
  const u = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, '');
  if (u) return u;
  return '/api';
}

function url(path: string): string {
  const p = path.startsWith('/') ? path : `/${path}`;
  return `${apiBase()}${p}`;
}

export async function fetchStreamQuery(
  query: string,
  topK: number = 5,
  documentIds?: string[],
  onEvent?: (event: SSEEvent) => void,
): Promise<void> {
  const res = await fetch(url('/query/stream'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, top_k: topK, document_ids: documentIds }),
  });
  if (!res.ok) throw new Error(`Stream failed: ${res.status} ${res.statusText}`);

  const reader = res.body?.getReader();
  if (!reader) throw new Error('No response body');

  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          onEvent?.(JSON.parse(line.slice(6)) as SSEEvent);
        } catch {
          /* skip malformed */
        }
      }
    }
  }
  onEvent?.({ type: 'done' });
}

export async function queryDocuments(
  query: string,
  topK = 5,
  documentIds?: string[],
): Promise<AnswerResponse> {
  const res = await fetch(url('/query'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, top_k: topK, document_ids: documentIds }),
  });
  if (!res.ok) throw new Error(`Query failed: ${res.status} ${res.statusText}`);
  return res.json();
}

export async function uploadDocument(file: File): Promise<{
  document_id: string;
  filename: string;
  file_type: string;
  status: string;
  message: string;
}> {
  const formData = new FormData();
  formData.append('file', file);
  const res = await fetch(url('/upload'), { method: 'POST', body: formData });
  if (!res.ok) {
    const t = await res.text();
    throw new Error(t || `Upload failed: ${res.status}`);
  }
  return res.json();
}

export async function getDocuments(): Promise<DocumentInfo[]> {
  const res = await fetch(url('/documents'));
  if (!res.ok) throw new Error(`List failed: ${res.statusText}`);
  return res.json();
}

export async function getDocument(id: string): Promise<DocumentInfo> {
  const res = await fetch(url(`/documents/${id}`));
  if (!res.ok) throw new Error(`Get document failed: ${res.statusText}`);
  return res.json();
}

export async function retrieveChunks(
  query: string,
  topK = 5,
  documentIds?: string[],
) {
  const res = await fetch(url('/retrieve'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, top_k: topK, document_ids: documentIds }),
  });
  if (!res.ok) throw new Error(`Retrieve failed: ${res.statusText}`);
  return res.json();
}

export async function submitFeedback(
  query: string,
  answer: string,
  rating: number,
  correction?: string,
  documentIds?: string[],
): Promise<void> {
  const res = await fetch(url('/feedback'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query,
      answer,
      rating,
      correction,
      document_ids: documentIds,
    }),
  });
  if (!res.ok) throw new Error(`Feedback failed: ${res.statusText}`);
}

export async function compareDocuments(
  documentIds: [string, string],
  focus?: string,
): Promise<CompareResponse> {
  const res = await fetch(url('/compare'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ document_ids: documentIds, focus: focus || null }),
  });
  if (!res.ok) {
    const t = await res.text();
    throw new Error(t || `Compare failed: ${res.status}`);
  }
  return res.json();
}
