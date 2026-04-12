import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'DocuMind AI — Document Intelligence',
  description: 'Enterprise document intelligence platform with agentic RAG',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-surface-1 text-ink-0 min-h-screen">{children}</body>
    </html>
  );
}
