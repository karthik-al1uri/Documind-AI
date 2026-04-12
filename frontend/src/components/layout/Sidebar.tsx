'use client';

import { FileText, Loader2 } from 'lucide-react';
import type { DocumentInfo } from '@/types';

interface Props {
  documents: DocumentInfo[];
  activeDocumentId: string | null;
  onSelectDocument: (id: string | null) => void;
  uploadSlot: React.ReactNode;
}

function statusDot(status: string) {
  if (status === 'processing' || status === 'pending')
    return <Loader2 className="h-3 w-3 text-dm-accent animate-spin shrink-0" />;
  if (status === 'completed') return <span className="h-2 w-2 rounded-full bg-dm-success shrink-0" />;
  if (status === 'needs_review') return <span className="h-2 w-2 rounded-full bg-dm-warning shrink-0" />;
  return <span className="h-2 w-2 rounded-full bg-dm-danger shrink-0" />;
}

export function Sidebar({
  documents,
  activeDocumentId,
  onSelectDocument,
  uploadSlot,
}: Props) {
  return (
    <aside className="w-60 shrink-0 flex flex-col border-r border-dm-border bg-dm-bg min-h-0">
      <div className="p-4 border-b border-dm-border">
        <div className="flex items-center gap-2">
          <div className="h-8 w-8 rounded-lg bg-dm-accent/20 flex items-center justify-center">
            <FileText className="h-4 w-4 text-dm-accent" strokeWidth={1.5} />
          </div>
          <div>
            <p className="text-sm font-semibold text-dm-text tracking-tight">DocuMind.ai</p>
            <p className="text-[10px] text-dm-muted uppercase tracking-wider">Enterprise</p>
          </div>
        </div>
      </div>

      <div className="p-3 space-y-3 border-b border-dm-border">{uploadSlot}</div>

      <div className="flex-1 overflow-y-auto px-2 py-3">
        <p className="text-[10px] uppercase tracking-widest text-dm-muted font-semibold px-2 mb-2">
          Documents
        </p>
        {documents.length === 0 ? (
          <div className="px-2 py-10 text-center text-xs text-dm-muted">
            <FileText className="h-8 w-8 mx-auto mb-2 opacity-40" />
            No documents yet
          </div>
        ) : (
          <ul className="space-y-0.5">
            {documents.map((doc) => {
              const active = doc.id === activeDocumentId;
              return (
                <li key={doc.id}>
                  <button
                    type="button"
                    onClick={() => onSelectDocument(active ? null : doc.id)}
                    className={`w-full flex items-center gap-2 px-2 py-2 rounded-md text-left text-sm transition-colors ${
                      active
                        ? 'bg-dm-surface text-dm-text border-l-2 border-dm-accent pl-[6px]'
                        : 'text-dm-muted hover:bg-dm-surface/80 border-l-2 border-transparent'
                    }`}
                  >
                    {statusDot(doc.status)}
                    <span className="truncate flex-1">{doc.filename}</span>
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </aside>
  );
}
