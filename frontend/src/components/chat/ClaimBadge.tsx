'use client';

import { Claim } from '@/types';

function tier(p: number) {
  if (p >= 0.85) return { label: 'Verified', dot: 'bg-dm-success', text: 'text-dm-success' };
  if (p >= 0.6) return { label: 'Partial', dot: 'bg-dm-warning', text: 'text-dm-warning' };
  return { label: 'Low confidence', dot: 'bg-dm-danger', text: 'text-dm-danger' };
}

export function ClaimBadge({ claim }: { claim: Claim }) {
  const p = claim.confidence ?? 0;
  const t = tier(p);
  const title = `"${claim.text}" — ${(p * 100).toFixed(0)}%${
    claim.entailment_label ? ` · ${claim.entailment_label}` : ''
  }`;
  return (
    <span
      title={title}
      className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-medium bg-dm-surface border border-dm-border ${t.text}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${t.dot}`} />
      {t.label} · {(p * 100).toFixed(0)}%
    </span>
  );
}
