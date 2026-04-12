'use client';

import { X, FileText } from 'lucide-react';
import { RetrievalResult } from '@/types';

interface Props {
  source: RetrievalResult;
  onClose: () => void;
}

export function DocumentViewer({ source, onClose }: Props) {
  const bbox = source.bbox;

  return (
    <aside className="panel-slide-in w-[380px] shrink-0 border-l border-dm-border bg-dm-bg flex flex-col h-full min-h-0">
      <div className="flex items-center justify-between px-4 py-3 border-b border-dm-border">
        <div className="flex items-center gap-2 min-w-0">
          <FileText size={16} className="text-dm-accent shrink-0" />
          <div className="min-w-0">
            <p className="text-sm font-medium text-dm-text truncate">{source.source_filename}</p>
            <p className="text-[10px] text-dm-muted">
              Page {source.page_number}
              {source.section_heading ? ` · ${source.section_heading}` : ''}
            </p>
          </div>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="p-1.5 rounded-md hover:bg-dm-surface text-dm-muted hover:text-dm-text transition-colors"
          aria-label="Close"
        >
          <X size={16} />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        <div
          className="relative bg-dm-surface border border-dm-border rounded-lg min-h-[480px]"
          style={{ aspectRatio: '8.5/11' }}
        >
          <div className="absolute inset-0 p-6 flex flex-col">
            <div className="absolute top-2 right-2 text-[10px] text-dm-muted bg-dm-bg px-1.5 py-0.5 rounded border border-dm-border">
              p. {source.page_number}
            </div>

            {source.section_heading && (
              <div className="mb-4">
                <div className="h-2 w-32 bg-dm-border rounded mb-2" />
                <p className="text-xs font-semibold text-dm-text">{source.section_heading}</p>
              </div>
            )}

            <div className="space-y-1.5 mb-3">
              {[0, 1, 2].map((i) => (
                <div
                  key={`pre-${i}`}
                  className="h-1.5 bg-dm-border rounded"
                  style={{ width: `${70 + (i % 3) * 10}%` }}
                />
              ))}
            </div>

            <div className="citation-highlight rounded-md p-3 mb-3">
              <p className="text-xs text-dm-text leading-relaxed">{source.text}</p>
            </div>

            <div className="space-y-1.5">
              {[0, 1, 2, 3, 4].map((i) => (
                <div
                  key={`post-${i}`}
                  className="h-1.5 bg-dm-border rounded"
                  style={{ width: `${60 + (i % 4) * 8}%` }}
                />
              ))}
            </div>
          </div>

          {bbox && (
            <div
              className="absolute border-2 border-dm-accent bg-dm-accent/5 rounded pointer-events-none"
              style={{
                left: `${(bbox.x0 / 612) * 100}%`,
                top: `${(bbox.y0 / 792) * 100}%`,
                width: `${((bbox.x1 - bbox.x0) / 612) * 100}%`,
                height: `${((bbox.y1 - bbox.y0) / 792) * 100}%`,
              }}
            />
          )}
        </div>
      </div>

      <div className="px-4 py-3 border-t border-dm-border grid grid-cols-2 gap-2 text-[10px]">
        <div>
          <span className="text-dm-muted">Score</span>
          <p className="text-dm-text font-medium">{(source.score * 100).toFixed(1)}%</p>
        </div>
        {bbox && (
          <div>
            <span className="text-dm-muted">Region</span>
            <p className="text-dm-muted font-mono text-[9px]">
              {bbox.x0.toFixed(0)},{bbox.y0.toFixed(0)} — {bbox.x1.toFixed(0)},{bbox.y1.toFixed(0)}
            </p>
          </div>
        )}
      </div>
    </aside>
  );
}
