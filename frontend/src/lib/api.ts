/**
 * API client for communicating with the DocuMind AI backend.
 * All endpoints proxy through Next.js rewrites to http://localhost:8000.
 */

import { AnswerResponse, DocumentInfo, SSEEvent } from '@/types';

const BASE = '/api';

export async function fetchStreamQuery(
  query: string,
  topK: number = 5,
  documentIds?: string[],
  onEvent?: (event: SSEEvent) => void,
): Promise<void> {
  const res = await fetch(`${BASE}/query/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, top_k: topK, document_ids: documentIds }),
  });
  if (!res.ok) throw new Error(`Stream failed: ${res.statusText}`);

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
        try { onEvent?.(JSON.parse(line.slice(6))); } catch { /* skip */ }
      }
    }
  }
}

export async function queryDocuments(
  query: string, topK = 5, documentIds?: string[],
): Promise<AnswerResponse> {
  const res = await fetch(`${BASE}/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, top_k: topK, document_ids: documentIds }),
  });
  if (!res.ok) throw new Error(`Query failed: ${res.statusText}`);
  return res.json();
}

export async function uploadDocument(file: File): Promise<{ document_id: string }> {
  const formData = new FormData();
  formData.append('file', file);
  const res = await fetch(`${BASE}/upload`, { method: 'POST', body: formData });
  if (!res.ok) throw new Error(`Upload failed: ${res.statusText}`);
  return res.json();
}

export async function listDocuments(): Promise<DocumentInfo[]> {
  const res = await fetch(`${BASE}/documents`);
  if (!res.ok) throw new Error(`List failed: ${res.statusText}`);
  return res.json();
}

export async function submitFeedback(
  query: string, answer: string, rating: number,
  correction?: string, documentIds?: string[],
): Promise<void> {
  await fetch(`${BASE}/feedback`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, answer, rating, correction, document_ids: documentIds }),
  });
}
