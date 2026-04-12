'use client';

import { Search, Sparkles, ShieldCheck, RefreshCw } from 'lucide-react';

const STAGES: Record<string, { label: string; icon: React.ReactNode; color: string }> = {
  retrieving: { label: 'Searching documents…', icon: <Search size={14} />, color: 'text-brand-500' },
  generating: { label: 'Generating answer…', icon: <Sparkles size={14} />, color: 'text-amber-500' },
  verifying:  { label: 'Verifying claims via NLI…', icon: <ShieldCheck size={14} />, color: 'text-green-600' },
  retrying:   { label: 'Refining query…', icon: <RefreshCw size={14} />, color: 'text-orange-500' },
};

export function StageIndicator({ stage }: { stage: string }) {
  const info = STAGES[stage] || STAGES.retrieving;
  return (
    <div className="flex items-center gap-3 px-4 py-2 animate-fade-in-up">
      <div className="w-8 h-8 rounded-lg bg-surface-2 flex items-center justify-center shrink-0">
        <span className={`animate-pulse ${info.color}`}>{info.icon}</span>
      </div>
      <span className="text-xs text-ink-3">{info.label}</span>
    </div>
  );
}
