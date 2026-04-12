'use client';

import { useCallback, useRef, useState } from 'react';
import { UploadCloud } from 'lucide-react';
import { uploadDocument } from '@/lib/api';

interface Props {
  onUploadComplete: (documentId: string, filename: string) => void;
}

export function UploadZone({ onUploadComplete }: Props) {
  const [dragOver, setDragOver] = useState(false);
  const [progress, setProgress] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [doneName, setDoneName] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const runUpload = async (file: File) => {
    setError(null);
    setDoneName(null);
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setError('Only PDF files are supported.');
      return;
    }
    setProgress(10);
    try {
      const interval = window.setInterval(() => {
        setProgress((p) => (p !== null && p < 90 ? p + 12 : p));
      }, 120);
      const res = await uploadDocument(file);
      window.clearInterval(interval);
      setProgress(100);
      setDoneName(file.name);
      onUploadComplete(res.document_id, file.name);
      window.setTimeout(() => {
        setProgress(null);
      }, 800);
    } catch (e) {
      setProgress(null);
      setError(e instanceof Error ? e.message : 'Upload failed');
    }
  };

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      const f = e.dataTransfer.files?.[0];
      if (f) void runUpload(f);
    },
    [onUploadComplete],
  );

  return (
    <div className="w-full">
      <button
        type="button"
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
        className={`w-full rounded-lg border-2 border-dashed px-4 py-8 text-center transition-colors ${
          dragOver
            ? 'border-dm-accent bg-dm-accent/10'
            : 'border-dm-border bg-dm-surface hover:border-dm-accent/60'
        }`}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,application/pdf"
          className="hidden"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) void runUpload(f);
            e.target.value = '';
          }}
        />
        <UploadCloud className="mx-auto h-10 w-10 text-dm-muted mb-3" strokeWidth={1.25} />
        <p className="text-sm font-medium text-dm-text">Drop your PDF here</p>
        <p className="text-xs text-dm-muted mt-1">or click to browse</p>
      </button>

      {progress !== null && (
        <div className="mt-3 h-1.5 w-full rounded-full bg-dm-border overflow-hidden">
          <div
            className="h-full bg-dm-accent transition-all duration-200"
            style={{ width: `${progress}%` }}
          />
        </div>
      )}

      {doneName && (
        <p className="mt-2 text-xs text-dm-success">Uploaded: {doneName}</p>
      )}
      {error && <p className="mt-2 text-xs text-dm-danger">{error}</p>}
    </div>
  );
}
