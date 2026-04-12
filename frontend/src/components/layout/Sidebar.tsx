'use client';

import { useState, useRef, useEffect } from 'react';
import { FileText, Plus, Settings } from 'lucide-react';
import { uploadDocument, listDocuments } from '@/lib/api';
import { DocumentInfo } from '@/types';

interface Props {
  onDocumentSelect: (ids: string[]) => void;
}

export function Sidebar({ onDocumentSelect }: Props) {
  const [documents, setDocuments] = useState<DocumentInfo[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [uploading, setUploading] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    listDocuments().then(setDocuments).catch(() => {});
  }, []);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      await uploadDocument(file);
      const docs = await listDocuments();
      setDocuments(docs);
    } catch (err) {
      console.error('Upload failed:', err);
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = '';
    }
  };

  const toggleDoc = (id: string) => {
    const next = new Set(selected);
    next.has(id) ? next.delete(id) : next.add(id);
    setSelected(next);
    onDocumentSelect(Array.from(next));
  };

  const statusColor: Record<string, string> = {
    completed: 'bg-green-50 text-green-700',
    processing: 'bg-yellow-50 text-yellow-700',
    needs_review: 'bg-red-50 text-red-700',
    pending: 'bg-surface-2 text-ink-3',
  };

  return (
    <aside className="w-64 bg-white border-r border-surface-3 flex flex-col shrink-0">
      <div className="p-5 border-b border-surface-3">
        <h1 className="font-display text-2xl text-brand-700 tracking-tight">
          DocuMind<span className="text-brand-400">.ai</span>
        </h1>
        <p className="text-[10px] text-ink-3 mt-0.5 tracking-wide">Document Intelligence Platform</p>
      </div>

      <div className="p-3">
        <button onClick={() => fileRef.current?.click()} disabled={uploading}
          className="w-full flex items-center gap-2 px-3 py-2.5 rounded-lg bg-brand-600 text-white text-sm font-medium hover:bg-brand-700 transition-colors disabled:opacity-50">
          {uploading
            ? <span className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full" />
            : <Plus size={16} />}
          {uploading ? 'Uploading…' : 'Upload Document'}
        </button>
        <input ref={fileRef} type="file" accept=".pdf,.png,.jpg,.jpeg" onChange={handleUpload} className="hidden" />
      </div>

      <div className="flex-1 overflow-y-auto px-3 py-2">
        <p className="text-[10px] uppercase tracking-widest text-ink-4 font-semibold mb-2 px-1">Documents</p>
        {documents.length === 0 ? (
          <div className="text-center py-8 text-ink-4 text-xs">
            <FileText size={28} className="mx-auto mb-2 opacity-40" />
            No documents yet
          </div>
        ) : (
          <ul className="space-y-0.5">
            {documents.map((doc) => (
              <li key={doc.id} onClick={() => toggleDoc(doc.id)}
                className={`flex items-center gap-2 px-2 py-2 rounded-md cursor-pointer transition-colors text-sm
                  ${selected.has(doc.id) ? 'bg-brand-50 border border-brand-200' : 'hover:bg-surface-2'}`}>
                <FileText size={14} className="text-ink-3 shrink-0" />
                <span className="truncate text-ink-1 flex-1">{doc.filename}</span>
                <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${statusColor[doc.status] || statusColor.pending}`}>
                  {doc.status}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="p-3 border-t border-surface-3">
        <button className="flex items-center gap-2 text-xs text-ink-3 hover:text-ink-1 transition-colors px-1">
          <Settings size={14} /> Settings
        </button>
      </div>
    </aside>
  );
}
