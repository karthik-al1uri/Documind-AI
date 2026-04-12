'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { Sidebar } from '@/components/layout/Sidebar';
import { ChatPanel } from '@/components/chat/ChatPanel';
import { DocumentViewer } from '@/components/document/DocumentViewer';
import { UploadZone } from '@/components/upload/UploadZone';
import { ComparisonPanel } from '@/components/comparison/ComparisonPanel';
import { getDocuments } from '@/lib/api';
import { RetrievalResult, DocumentInfo } from '@/types';

export default function Home() {
  const [documents, setDocuments] = useState<DocumentInfo[]>([]);
  const [activeDocumentId, setActiveDocumentId] = useState<string | null>(null);
  const [selectedSource, setSelectedSource] = useState<RetrievalResult | null>(null);
  const [showViewer, setShowViewer] = useState(false);
  const [compareOpen, setCompareOpen] = useState(false);

  const refreshDocuments = useCallback(async () => {
    const list = await getDocuments();
    setDocuments(list);
    return list;
  }, []);

  useEffect(() => {
    void refreshDocuments();
  }, [refreshDocuments]);

  const activeDocument = useMemo(
    () => documents.find((d) => d.id === activeDocumentId) || null,
    [documents, activeDocumentId],
  );

  const chatDocumentIds = useMemo(
    () => (activeDocumentId ? [activeDocumentId] : undefined),
    [activeDocumentId],
  );

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-dm-bg">
      <header className="h-12 shrink-0 border-b border-dm-border flex items-center px-4 gap-4 bg-dm-bg">
        <span className="text-sm font-semibold text-dm-text">DocuMind.ai</span>
        <span className="text-dm-border">|</span>
        <span className="text-xs text-dm-muted truncate flex-1 text-center">
          {activeDocument ? activeDocument.filename : 'No document selected'}
        </span>
        <button
          type="button"
          onClick={() => setCompareOpen(true)}
          disabled={documents.length < 2}
          className="text-xs px-3 py-1.5 rounded-md border border-dm-border text-dm-text hover:bg-dm-surface disabled:opacity-40"
        >
          Compare documents
        </button>
      </header>

      <div className="flex flex-1 min-h-0">
        <Sidebar
          documents={documents}
          activeDocumentId={activeDocumentId}
          onSelectDocument={setActiveDocumentId}
          uploadSlot={
            <UploadZone
              onUploadComplete={async (documentId, _filename) => {
                const list = await refreshDocuments();
                setActiveDocumentId(documentId);
                const done = list.find((d) => d.id === documentId);
                if (done && done.status !== 'completed') {
                  const t0 = Date.now();
                  while (Date.now() - t0 < 120000) {
                    await new Promise((r) => setTimeout(r, 2000));
                    const again = await refreshDocuments();
                    const u = again.find((d) => d.id === documentId);
                    if (u && (u.status === 'completed' || u.status === 'needs_review')) break;
                  }
                }
              }}
            />
          }
        />

        <ChatPanel
          activeDocument={activeDocument}
          documentIds={chatDocumentIds}
          onSourceClick={(src) => {
            setSelectedSource(src);
            setShowViewer(true);
          }}
        />

        {showViewer && selectedSource && (
          <DocumentViewer
            source={selectedSource}
            onClose={() => {
              setShowViewer(false);
              setSelectedSource(null);
            }}
          />
        )}
      </div>

      {compareOpen && (
        <ComparisonPanel
          documents={documents}
          onClose={() => setCompareOpen(false)}
        />
      )}
    </div>
  );
}
