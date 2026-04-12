/**
 * React hook for chat state management with SSE streaming (POST /query/stream).
 */

'use client';

import { useState, useCallback } from 'react';
import { ChatMessage, SSEEvent } from '@/types';
import { fetchStreamQuery } from '@/lib/api';

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [currentStage, setCurrentStage] = useState<string | null>(null);

  const sendMessage = useCallback(async (query: string, documentIds?: string[]) => {
    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: query,
      timestamp: new Date(),
    };
    const assistantMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'assistant',
      content: '',
      timestamp: new Date(),
      status: 'streaming',
    };

    setMessages((prev) => [...prev, userMsg, assistantMsg]);
    setIsLoading(true);
    setCurrentStage('retrieving');

    try {
      await fetchStreamQuery(query, 5, documentIds, (event: SSEEvent) => {
        switch (event.type) {
          case 'status':
            setCurrentStage(event.stage || null);
            break;
          case 'token':
            setMessages((prev) => {
              const updated = [...prev];
              const last = updated[updated.length - 1];
              if (last.role === 'assistant') last.content += event.text || '';
              return updated;
            });
            break;
          case 'answer':
            setMessages((prev) => {
              const updated = [...prev];
              const last = updated[updated.length - 1];
              if (last.role === 'assistant') {
                last.answer_response = event.data;
                last.content = event.data?.answer || last.content;
                last.status = 'complete';
              }
              return updated;
            });
            break;
          case 'done':
            setCurrentStage(null);
            break;
          case 'error':
            setMessages((prev) => {
              const updated = [...prev];
              const last = updated[updated.length - 1];
              if (last.role === 'assistant') {
                last.content = `Error: ${event.message}`;
                last.status = 'error';
              }
              return updated;
            });
            setIsLoading(false);
            setCurrentStage(null);
            break;
        }
      });
    } catch (err) {
      setMessages((prev) => {
        const updated = [...prev];
        const last = updated[updated.length - 1];
        if (last.role === 'assistant') {
          last.content = `Connection error: ${String(err)}`;
          last.status = 'error';
        }
        return updated;
      });
    } finally {
      setIsLoading(false);
      setCurrentStage(null);
    }
  }, []);

  const clearMessages = useCallback(() => setMessages([]), []);

  return { messages, isLoading, currentStage, sendMessage, clearMessages };
}
