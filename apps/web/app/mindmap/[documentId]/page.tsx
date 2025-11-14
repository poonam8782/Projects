import React from 'react';
import MindmapViewerUnified from '@/components/MindmapViewerUnified';
import { notFound } from 'next/navigation';

interface MindmapPageProps {
  params: { documentId?: string };
  searchParams?: Record<string, string | string[]>;
}

// Standalone page to view a generated mindmap full screen without modal constraints.
// Usage: /mindmap/<documentId>
export default function MindmapPage({ params }: MindmapPageProps) {
  const documentId = params.documentId;
  if (!documentId) {
    return notFound();
  }
  return (
    <div className="min-h-screen w-full bg-black text-white flex flex-col">
      <header className="px-6 py-4 border-b border-border-ui flex items-center justify-between bg-surface-ui">
        <h1 className="text-lg font-semibold">Mindmap Viewer</h1>
        <a
          href={`/document/${documentId}`}
          className="text-sm underline hover:no-underline"
        >Back to Document</a>
      </header>
      <main className="flex-1 overflow-hidden">
        <MindmapViewerUnified documentId={documentId} documentName={documentId} showControls allowFullscreen bare />
      </main>
    </div>
  );
}
