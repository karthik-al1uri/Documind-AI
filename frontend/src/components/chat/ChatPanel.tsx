'use client';

import { useRef, useEffect } from 'react';
import { useChat } from '@/hooks/useChat';
import { ChatMessageBubble } from '@/components/chat/ChatMessage';
import { ChatInput } from '@/components/chat/ChatInput';
import { StageIndicator } from '@/components/chat/StageIndicator';
import { RetrievalResult, DocumentInfo } from '@/types';

interface Props {
  activeDocument: DocumentInfo | null;
  documentIds?: string[];
  onSourceClick: (source: RetrievalResult) => void;
}

export function ChatPanel({ activeDocument, documentIds, onSourceClick }: Props) {
  const { messages, isLoading, currentStage, sendMessage } = useChat();
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, currentStage]);

  const suggestions = [
    'What are the payment terms?',
    'Who are the parties to this agreement?',
    'What is the effective date?',
  ];

  const scopeIds = documentIds && documentIds.length > 0 ? documentIds : undefined;

  return (
    <div className="flex-1 flex flex-col bg-dm-bg min-w-0 min-h-0">
      <div className="h-12 shrink-0 border-b border-dm-border flex items-center px-4 gap-2">
        {activeDocument ? (
          <span className="inline-flex items-center rounded-full border border-dm-border bg-dm-surface px-3 py-1 text-xs text-dm-text">
            {activeDocument.filename}
          </span>
        ) : (
          <span className="text-xs text-dm-muted">No document selected</span>
        )}
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-6">
        {!activeDocument && messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center max-w-md mx-auto py-12">
            <p className="text-dm-text text-lg font-medium mb-2">Upload a document to start asking questions</p>
            <p className="text-dm-muted text-sm">
              Select a document from the sidebar after upload, then ask grounded questions with citations.
            </p>
          </div>
        ) : messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center max-w-md mx-auto">
            <p className="text-dm-text text-lg font-medium mb-2">Ask anything about your documents</p>
            <div className="flex flex-col gap-2 mt-6 w-full">
              {suggestions.map((q) => (
                <button
                  key={q}
                  type="button"
                  onClick={() => void sendMessage(q, scopeIds)}
                  className="px-4 py-2 text-sm rounded-lg border border-dm-border bg-dm-surface text-dm-muted hover:border-dm-accent hover:text-dm-text transition-colors text-left"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="max-w-3xl mx-auto space-y-1">
            {messages.map((msg, i) => (
              <ChatMessageBubble
                key={msg.id}
                message={msg}
                userQuery={
                  msg.role === 'assistant' && i > 0 && messages[i - 1].role === 'user'
                    ? messages[i - 1].content
                    : undefined
                }
                onSourceClick={onSourceClick}
              />
            ))}
            {isLoading && currentStage && <StageIndicator stage={currentStage} />}
            <div ref={bottomRef} />
          </div>
        )}
      </div>
      <ChatInput
        onSend={(q) => void sendMessage(q, scopeIds)}
        disabled={isLoading || !activeDocument}
      />
    </div>
  );
}
