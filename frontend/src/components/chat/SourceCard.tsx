'use client';

import { RetrievalResult } from '@/types';

interface Props {
  source: RetrievalResult;
  index: number;
  onClick: () => void;
}

export function SourceCard({ source, index, onClick }: Props) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="flex items-start gap-2 px-3 py-2 rounded-lg border border-dm-border bg-dm-surface hover:border-dm-accent/50 transition-all text-left min-w-[180px] max-w-[240px] shrink-0"
    >
      <div className="w-5 h-5 rounded bg-dm-accent/20 flex items-center justify-center shrink-0 mt-0.5">
        <span className="text-[10px] font-bold text-dm-accent">{index + 1}</span>
      </div>
      <div className="min-w-0">
        <p className="text-xs font-medium text-dm-text truncate">{source.source_filename}</p>
        <p className="text-[10px] text-dm-muted mt-0.5">
          Page {source.page_number} · Score {(source.score * 100).toFixed(0)}%
        </p>
        <p className="text-[10px] text-dm-muted mt-1 line-clamp-2 leading-relaxed">
          {source.text.slice(0, 120)}
          {source.text.length > 120 ? '…' : ''}
        </p>
      </div>
    </button>
  );
}
