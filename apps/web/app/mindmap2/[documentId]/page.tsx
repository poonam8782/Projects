"use client";
import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import MindmapFlow from '@/components/MindmapFlow';
import { getMindmapData, MindmapNode } from '@/services/api';
import { Card, Button } from '@neura/ui';

export default function MindmapFlowPage() {
  const { documentId } = useParams<{ documentId: string }>();
  const [root, setRoot] = useState<MindmapNode | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const data = await getMindmapData(documentId);
        setRoot(data.root);
      } catch (e: any) {
        setError(e?.message ?? 'Failed to load mindmap');
      }
    })();
  }, [documentId]);

  if (error) {
    return (
      <div className="min-h-screen p-6">
        <Card className="p-6 bg-surface-ui border-border-ui">
          <p className="text-text-ui">{error}</p>
          <Button className="mt-4" onClick={() => location.reload()}>Retry</Button>
        </Card>
      </div>
    );
  }
  if (!root) {
    return <div className="min-h-screen p-6 text-muted-ui">Loading mindmap…</div>;
  }
  return (
    <div className="w-screen h-screen bg-white">
      <MindmapFlow root={root} />
    </div>
  );
}
