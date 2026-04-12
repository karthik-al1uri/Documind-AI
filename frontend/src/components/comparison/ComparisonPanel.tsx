'use client';

import { useEffect, useState } from 'react';
import { X } from 'lucide-react';
import { compareDocuments } from '@/lib/api';
import type { CompareResponse, DocumentInfo } from '@/types';

interface Props {
  documents: DocumentInfo[];
  onClose: () => void;
}

export function ComparisonPanel({ documents, onClose }: Props) {
  const [docA, setDocA] = useState('');
  const [docB, setDocB] = useState('');
  const [focus, setFocus] = useState('payment terms');
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [result, setResult] = useState<CompareResponse | null>(null);

  useEffect(() => {
    if (documents.length >= 2) {
      setDocA(documents[0].id);
      setDocB(documents[1].id);
    } else if (documents.length === 1) {
      setDocA(documents[0].id);
      setDocB('');
    }
  }, [documents]);

  const run = async () => {
    if (!docA || !docB || docA === docB) {
      setErr('Select two different documents.');
      return;
    }
    setErr(null);
    setLoading(true);
    setResult(null);
    try {
      const res = await compareDocuments([docA, docB], focus.trim() || undefined);
      setResult(res);
    } catch (e) {
      setErr(e instanceof Error ? e.message : 'Compare failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
      <div className="bg-dm-bg border border-dm-border rounded-xl max-w-5xl w-full max-h-[90vh] flex flex-col shadow-2xl">
        <div className="flex items-center justify-between px-5 py-4 border-b border-dm-border">
          <h2 className="text-lg font-semibold text-dm-text">Compare documents</h2>
          <button
            type="button"
            onClick={onClose}
            className="p-2 rounded-lg text-dm-muted hover:text-dm-text hover:bg-dm-surface"
            aria-label="Close"
          >
            <X size={20} />
          </button>
        </div>

        <div className="px-5 py-4 border-b border-dm-border grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs text-dm-muted mb-1">Document 1</label>
            <select
              value={docA}
              onChange={(e) => setDocA(e.target.value)}
              className="w-full rounded-lg bg-dm-surface border border-dm-border px-3 py-2 text-sm text-dm-text"
            >
              <option value="">Select…</option>
              {documents.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.filename}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs text-dm-muted mb-1">Document 2</label>
            <select
              value={docB}
              onChange={(e) => setDocB(e.target.value)}
              className="w-full rounded-lg bg-dm-surface border border-dm-border px-3 py-2 text-sm text-dm-text"
            >
              <option value="">Select…</option>
              {documents.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.filename}
                </option>
              ))}
            </select>
          </div>
          <div className="md:col-span-2">
            <label className="block text-xs font-medium text-dm-muted uppercase tracking-wide mb-1">
              What would you like to compare?
            </label>
            <input
              value={focus}
              onChange={(e) => setFocus(e.target.value)}
              className="w-full rounded-lg bg-dm-surface border border-dm-border px-3 py-2 text-sm text-dm-text"
              placeholder="Topic or clause focus"
            />
          </div>
          <div className="md:col-span-2">
            <button
              type="button"
              disabled={loading || documents.length < 2}
              onClick={() => void run()}
              className="px-4 py-2 rounded-lg bg-dm-accent text-white text-sm font-medium hover:bg-dm-accent-hover disabled:opacity-50"
            >
              {loading ? 'Comparing…' : 'Compare'}
            </button>
            {err && <p className="text-sm text-dm-danger mt-2">{err}</p>}
          </div>
        </div>

        <div className="flex-1 overflow-y-auto px-5 py-4">
          {result && (
            <>
              <p className="text-sm text-dm-text leading-relaxed mb-6">{result.summary}</p>
              <div className="overflow-x-auto rounded-lg border border-dm-border">
                <table className="w-full text-left text-sm">
                  <thead>
                    <tr className="bg-dm-surface border-b border-dm-border">
                      <th className="p-3 font-medium text-dm-muted">Topic</th>
                      <th className="p-3 font-medium text-dm-muted">{result.documents[0]}</th>
                      <th className="p-3 font-medium text-dm-muted">{result.documents[1]}</th>
                      <th className="p-3 font-medium text-dm-muted w-24">Similarity</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.differences.map((row, i) => (
                      <tr key={i} className="border-b border-dm-border align-top">
                        <td className="p-3 text-dm-text font-medium">{row.topic}</td>
                        <td className="p-3 text-dm-muted whitespace-pre-wrap max-w-md">{row.document_1}</td>
                        <td className="p-3 text-dm-muted whitespace-pre-wrap max-w-md">{row.document_2}</td>
                        <td className="p-3 text-dm-text tabular-nums">
                          {(row.similarity_score * 100).toFixed(0)}%
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
