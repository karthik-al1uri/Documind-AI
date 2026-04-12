'use client';

import { useState, useRef, useEffect } from 'react';
import { Send } from 'lucide-react';

interface Props { onSend: (query: string) => void; disabled: boolean; }

export function ChatInput({ onSend, disabled }: Props) {
  const [value, setValue] = useState('');
  const ref = useRef<HTMLTextAreaElement>(null);

  useEffect(() => { ref.current?.focus(); }, [disabled]);

  const submit = () => {
    const t = value.trim();
    if (!t || disabled) return;
    onSend(t);
    setValue('');
    if (ref.current) ref.current.style.height = 'auto';
  };

  return (
    <div className="border-t border-surface-3 bg-white px-4 py-3">
      <div className="max-w-3xl mx-auto flex items-end gap-2">
        <textarea ref={ref} value={value}
          onChange={e => setValue(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit(); } }}
          onInput={e => { const el = e.currentTarget; el.style.height = 'auto'; el.style.height = Math.min(el.scrollHeight, 120) + 'px'; }}
          placeholder="Ask a question about your documents…" disabled={disabled} rows={1}
          className="flex-1 resize-none rounded-xl border border-surface-3 px-4 py-2.5 text-sm text-ink-0 placeholder:text-ink-4
                     focus:outline-none focus:border-brand-400 focus:ring-2 focus:ring-brand-100 disabled:opacity-50 transition-all"
          style={{ minHeight: '42px', maxHeight: '120px' }} />
        <button onClick={submit} disabled={disabled || !value.trim()}
          className="p-2.5 rounded-xl bg-brand-600 text-white hover:bg-brand-700 disabled:opacity-30 transition-all shrink-0">
          <Send size={16} />
        </button>
      </div>
      <p className="text-center text-[10px] text-ink-4 mt-2">
        Answers grounded in your documents · Verified via NLI entailment
      </p>
    </div>
  );
}
