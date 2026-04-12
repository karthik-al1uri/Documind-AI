'use client';

import { useRef, useEffect } from 'react';
import { useChat } from '@/hooks/useChat';
import { ChatMessageBubble } from '@/components/chat/ChatMessage';
import { ChatInput } from '@/components/chat/ChatInput';
import { StageIndicator } from '@/components/chat/StageIndicator';
import { RetrievalResult } from '@/types';
import { Sparkles } from 'lucide-react';

interface Props {
  documentIds?: string[];
  onSourceClick: (source: RetrievalResult) => void;
}

export function ChatPanel({ documentIds, onSourceClick }: Props) {
  const { messages, isLoading, currentStage, sendMessage } = useChat();
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, currentStage]);

  const suggestions = [
    'What are the key terms in this contract?',
    'Summarize the findings in Section 3',
    'Compare the revenue figures across reports',
  ];

  return (
    <div className="flex-1 flex flex-col bg-surface-1 min-w-0">
      <div className="flex-1 overflow-y-auto px-4 py-6">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center max-w-md mx-auto">
            <div className="w-14 h-14 rounded-2xl bg-brand-100 flex items-center justify-center mb-4">
              <Sparkles className="text-brand-600" size={24} />
            </div>
            <h2 className="font-display text-3xl text-ink-0 mb-2">Ask your documents anything</h2>
            <p className="text-ink-3 text-sm leading-relaxed">
              Upload PDFs, contracts, or reports and get grounded answers with exact source citations verified by NLI.
            </p>
            <div className="flex gap-2 mt-6 flex-wrap justify-center">
              {suggestions.map((q) => (
                <button key={q} onClick={() => sendMessage(q, documentIds)}
                  className="px-3 py-1.5 text-xs bg-white border border-surface-3 rounded-full text-ink-2 hover:border-brand-300 hover:text-brand-600 transition-all">
                  {q}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="max-w-3xl mx-auto space-y-1">
            {messages.map((msg) => (
              <ChatMessageBubble key={msg.id} message={msg} onSourceClick={onSourceClick} />
            ))}
            {isLoading && currentStage && <StageIndicator stage={currentStage} />}
            <div ref={bottomRef} />
          </div>
        )}
      </div>
      <ChatInput onSend={(q) => sendMessage(q, documentIds)} disabled={isLoading} />
    </div>
  );
}
