'use client';

import { useState } from 'react';
import { Sidebar } from '@/components/layout/Sidebar';
import { ChatPanel } from '@/components/chat/ChatPanel';
import { DocumentViewer } from '@/components/document/DocumentViewer';
import { RetrievalResult } from '@/types';

export default function Home() {
  const [selectedSource, setSelectedSource] = useState<RetrievalResult | null>(null);
  const [showViewer, setShowViewer] = useState(false);
  const [selectedDocIds, setSelectedDocIds] = useState<string[]>([]);

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar onDocumentSelect={(ids) => setSelectedDocIds(ids)} />
      <main className="flex flex-1 overflow-hidden">
        <ChatPanel
          documentIds={selectedDocIds.length > 0 ? selectedDocIds : undefined}
          onSourceClick={(src) => { setSelectedSource(src); setShowViewer(true); }}
        />
        {showViewer && selectedSource && (
          <DocumentViewer source={selectedSource} onClose={() => setShowViewer(false)} />
        )}
      </main>
    </div>
  );
}
