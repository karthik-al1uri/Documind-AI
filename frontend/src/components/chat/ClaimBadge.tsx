'use client';

import { ShieldCheck, ShieldAlert, ShieldQuestion } from 'lucide-react';
import { Claim } from '@/types';

const CFG: Record<string, { icon: React.ReactNode; bg: string; text: string; ring: string }> = {
  entailment:    { icon: <ShieldCheck size={10} />,    bg: 'bg-green-50',  text: 'text-green-700',  ring: 'ring-green-200' },
  neutral:       { icon: <ShieldQuestion size={10} />, bg: 'bg-yellow-50', text: 'text-yellow-700', ring: 'ring-yellow-200' },
  contradiction: { icon: <ShieldAlert size={10} />,    bg: 'bg-red-50',    text: 'text-red-700',    ring: 'ring-red-200' },
};

export function ClaimBadge({ claim }: { claim: Claim }) {
  const label = claim.entailment_label || 'neutral';
  const c = CFG[label] || CFG.neutral;
  return (
    <span title={`"${claim.text}" — ${label} (${((claim.entailment_score || 0) * 100).toFixed(0)}%)`}
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium ring-1 ${c.bg} ${c.text} ${c.ring} ${label === 'entailment' ? 'badge-verified' : ''}`}>
      {c.icon} {((claim.confidence || 0) * 100).toFixed(0)}%
    </span>
  );
}
