'use client';

import { X, FileText, ExternalLink } from 'lucide-react';
import { RetrievalResult } from '@/types';

interface Props {
  source: RetrievalResult;
  onClose: () => void;
}

export function DocumentViewer({ source, onClose }: Props) {
  const bbox = source.bbox;

  return (
    <aside className="w-[420px] border-l border-surface-3 bg-white flex flex-col shrink-0 animate-fade-in-up">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-surface-3">
        <div className="flex items-center gap-2 min-w-0">
          <FileText size={16} className="text-brand-600 shrink-0" />
          <div className="min-w-0">
            <p className="text-sm font-medium text-ink-0 truncate">{source.source_filename}</p>
            <p className="text-[10px] text-ink-3">
              Page {source.page_number}
              {source.section_heading && ` · ${source.section_heading}`}
            </p>
          </div>
        </div>
        <button onClick={onClose}
          className="p-1.5 rounded-md hover:bg-surface-2 text-ink-3 hover:text-ink-1 transition-colors">
          <X size={16} />
        </button>
      </div>

      {/* Page mockup with bbox overlay */}
      <div className="flex-1 overflow-y-auto p-4">
        <div className="relative bg-surface-1 border border-surface-3 rounded-lg min-h-[500px]"
          style={{ aspectRatio: '8.5/11' }}>

          {/* Simulated page content area */}
          <div className="absolute inset-0 p-6 flex flex-col">
            {/* Page number badge */}
            <div className="absolute top-2 right-2 text-[10px] text-ink-4 bg-white px-1.5 py-0.5 rounded border border-surface-3">
              p. {source.page_number}
            </div>

            {/* Section heading if present */}
            {source.section_heading && (
              <div className="mb-4">
                <div className="h-2 w-32 bg-surface-3 rounded mb-2" />
                <p className="text-xs font-semibold text-ink-1">{source.section_heading}</p>
              </div>
            )}

            {/* Simulated lines before the highlight */}
            <div className="space-y-1.5 mb-3">
              {Array.from({ length: 3 }).map((_, i) => (
                <div key={`pre-${i}`} className="h-1.5 bg-surface-3 rounded" style={{ width: `${70 + Math.random() * 30}%` }} />
              ))}
            </div>

            {/* Highlighted citation region */}
            <div className="citation-highlight rounded-md p-3 mb-3">
              <p className="text-xs text-ink-0 leading-relaxed">{source.text}</p>
            </div>

            {/* Simulated lines after the highlight */}
            <div className="space-y-1.5">
              {Array.from({ length: 5 }).map((_, i) => (
                <div key={`post-${i}`} className="h-1.5 bg-surface-3 rounded" style={{ width: `${60 + Math.random() * 40}%` }} />
              ))}
            </div>
          </div>

          {/* BBox overlay if coordinates are available */}
          {bbox && (
            <div className="absolute border-2 border-brand-500 bg-brand-500/5 rounded pointer-events-none"
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

      {/* Metadata footer */}
      <div className="px-4 py-3 border-t border-surface-3 space-y-2">
        <div className="grid grid-cols-2 gap-2 text-[10px]">
          <div>
            <span className="text-ink-4">Document ID</span>
            <p className="text-ink-2 font-mono truncate">{source.document_id}</p>
          </div>
          <div>
            <span className="text-ink-4">Chunk ID</span>
            <p className="text-ink-2 font-mono truncate">{source.chunk_id}</p>
          </div>
          <div>
            <span className="text-ink-4">Score</span>
            <p className="text-ink-1 font-medium">{(source.score * 100).toFixed(1)}%</p>
          </div>
          {bbox && (
            <div>
              <span className="text-ink-4">BBox</span>
              <p className="text-ink-2 font-mono">
                ({bbox.x0.toFixed(0)},{bbox.y0.toFixed(0)}) → ({bbox.x1.toFixed(0)},{bbox.y1.toFixed(0)})
              </p>
            </div>
          )}
        </div>
      </div>
    </aside>
  );
}
