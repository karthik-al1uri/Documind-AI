'use client';

import { useState, useRef, useEffect } from 'react';
import { Send } from 'lucide-react';

interface Props {
  onSend: (query: string) => void;
  disabled: boolean;
}

export function ChatInput({ onSend, disabled }: Props) {
  const [value, setValue] = useState('');
  const ref = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    ref.current?.focus();
  }, [disabled]);

  const submit = () => {
    const t = value.trim();
    if (!t || disabled) return;
    onSend(t);
    setValue('');
    if (ref.current) ref.current.style.height = 'auto';
  };

  return (
    <div className="border-t border-dm-border bg-dm-bg px-4 py-3">
      <div className="max-w-3xl mx-auto flex items-end gap-2">
        <textarea
          ref={ref}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              submit();
            }
          }}
          onInput={(e) => {
            const el = e.currentTarget;
            el.style.height = 'auto';
            el.style.height = `${Math.min(el.scrollHeight, 120)}px`;
          }}
          placeholder="Ask a question about your documents…"
          disabled={disabled}
          rows={1}
          className="flex-1 resize-none rounded-xl border border-dm-border bg-dm-surface px-4 py-2.5 text-sm text-dm-text placeholder:text-dm-muted focus:outline-none focus:ring-1 focus:ring-dm-accent disabled:opacity-50 transition-all"
          style={{ minHeight: '42px', maxHeight: '120px' }}
        />
        <button
          type="button"
          onClick={submit}
          disabled={disabled || !value.trim()}
          className="p-2.5 rounded-xl bg-dm-accent text-white hover:bg-dm-accent-hover disabled:opacity-30 transition-all shrink-0"
        >
          <Send size={16} />
        </button>
      </div>
      <p className="text-center text-[10px] text-dm-muted mt-2">Shift+Enter for new line</p>
    </div>
  );
}
