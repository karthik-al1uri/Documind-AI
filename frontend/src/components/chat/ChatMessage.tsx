'use client';

import { ChatMessage, RetrievalResult } from '@/types';
import { ClaimBadge } from '@/components/chat/ClaimBadge';
import { SourceCard } from '@/components/chat/SourceCard';
import { FeedbackButtons } from '@/components/feedback/FeedbackButtons';

interface Props {
  message: ChatMessage;
  userQuery?: string;
  onSourceClick: (source: RetrievalResult) => void;
}

export function ChatMessageBubble({ message, userQuery, onSourceClick }: Props) {
  const isUser = message.role === 'user';
  const isStreaming = message.status === 'streaming';
  const resp = message.answer_response;

  return (
    <div
      className={`flex gap-3 animate-fade-in-up py-2 ${isUser ? 'justify-end' : 'justify-start'}`}
    >
      <div className={`max-w-[85%] ${isUser ? 'order-first' : ''}`}>
        <div
          className={`rounded-2xl px-4 py-3 text-sm leading-relaxed ${
            isUser
              ? 'bg-dm-accent text-white rounded-br-md'
              : 'bg-dm-surface border border-dm-border text-dm-text rounded-bl-md'
          } ${isStreaming ? 'streaming-cursor' : ''}`}
        >
          {message.content}
        </div>

        {resp && resp.claims.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1.5">
            {resp.claims.map((claim, i) => (
              <ClaimBadge key={i} claim={claim} />
            ))}
          </div>
        )}

        {resp && resp.sources.length > 0 && (
          <div className="mt-2 space-y-1">
            <p className="text-[10px] uppercase tracking-widest text-dm-muted font-semibold">
              Sources
            </p>
            <div className="flex gap-2 overflow-x-auto pb-1">
              {resp.sources.map((src, i) => (
                <SourceCard
                  key={src.chunk_id}
                  source={src}
                  index={i}
                  onClick={() => onSourceClick(src)}
                />
              ))}
            </div>
          </div>
        )}

        {resp && message.status === 'complete' && userQuery && (
          <FeedbackButtons query={userQuery} answer={resp.answer} />
        )}
      </div>
    </div>
  );
}
