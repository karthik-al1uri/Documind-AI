'use client';

import { Search, PenLine, ShieldCheck, RefreshCw } from 'lucide-react';

const STAGES: Record<string, { label: string; icon: React.ReactNode }> = {
  retrieving: { label: 'Searching documents…', icon: <Search size={14} /> },
  generating: { label: 'Generating answer…', icon: <PenLine size={14} /> },
  verifying: { label: 'Verifying claims…', icon: <ShieldCheck size={14} /> },
  retrying: { label: 'Refining query…', icon: <RefreshCw size={14} /> },
};

export function StageIndicator({ stage }: { stage: string }) {
  const info = STAGES[stage] || STAGES.retrieving;
  return (
    <div className="flex items-center gap-3 px-4 py-2 animate-fade-in-up">
      <div className="w-8 h-8 rounded-lg bg-dm-surface border border-dm-border flex items-center justify-center shrink-0">
        <span className="animate-pulse text-dm-accent">{info.icon}</span>
      </div>
      <span className="text-xs text-dm-muted">{info.label}</span>
    </div>
  );
}
