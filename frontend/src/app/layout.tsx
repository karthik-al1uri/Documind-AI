import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';

const inter = Inter({ subsets: ['latin'], variable: '--font-inter' });

export const metadata: Metadata = {
  title: 'DocuMind.ai — Enterprise document intelligence',
  description:
    'Agentic RAG over enterprise documents with grounded answers, citations, and verification.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={inter.variable}>
      <body className="min-h-screen bg-dm-bg text-dm-text antialiased">{children}</body>
    </html>
  );
}
