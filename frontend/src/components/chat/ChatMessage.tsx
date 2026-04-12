'use client';

import { ChatMessage, RetrievalResult } from '@/types';
import { ClaimBadge } from '@/components/chat/ClaimBadge';
import { SourceCard } from '@/components/chat/SourceCard';
import { FeedbackButtons } from '@/components/feedback/FeedbackButtons';
import { User, Sparkles } from 'lucide-react';

interface Props {
  message: ChatMessage;
  onSourceClick: (source: RetrievalResult) => void;
}

export function ChatMessageBubble({ message, onSourceClick }: Props) {
  const isUser = message.role === 'user';
  const isStreaming = message.status === 'streaming';
  const resp = message.answer_response;

  return (
    <div className={`flex gap-3 animate-fade-in-up py-2 ${isUser ? 'justify-end' : 'justify-start'}`}>
      {!isUser && (
        <div className="w-8 h-8 rounded-lg bg-brand-100 flex items-center justify-center shrink-0 mt-1">
          <Sparkles size={14} className="text-brand-600" />
        </div>
      )}

      <div className={`max-w-[85%] ${isUser ? 'order-first' : ''}`}>
        <div className={`rounded-2xl px-4 py-3 text-sm leading-relaxed
          ${isUser ? 'bg-brand-600 text-white rounded-br-md' : 'bg-white border border-surface-3 text-ink-0 rounded-bl-md shadow-sm'}
          ${isStreaming ? 'streaming-cursor' : ''}`}>
          {message.content}
        </div>

        {resp && resp.claims.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1.5">
            {resp.claims.map((claim, i) => <ClaimBadge key={i} claim={claim} />)}
          </div>
        )}

        {resp && resp.sources.length > 0 && (
          <div className="mt-2 space-y-1">
            <p className="text-[10px] uppercase tracking-widest text-ink-4 font-semibold">Sources</p>
            <div className="flex gap-2 overflow-x-auto pb-1">
              {resp.sources.map((src, i) => (
                <SourceCard key={src.chunk_id} source={src} index={i} onClick={() => onSourceClick(src)} />
              ))}
            </div>
          </div>
        )}

        {resp && message.status === 'complete' && (
          <FeedbackButtons query={message.content} answer={resp.answer} />
        )}
      </div>

      {isUser && (
        <div className="w-8 h-8 rounded-lg bg-ink-0 flex items-center justify-center shrink-0 mt-1">
          <User size={14} className="text-white" />
        </div>
      )}
    </div>
  );
}
