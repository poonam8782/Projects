'use client';

import React, { useEffect, useRef, useState } from 'react';

interface MarkmapRendererProps {
  content: string;
}

const MarkmapRenderer: React.FC<MarkmapRendererProps> = ({ content }) => {
  const svgRef = useRef<SVGSVGElement>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!content || !svgRef.current) return;

    let mounted = true;

    const renderMarkmap = async () => {
      try {
        const { Transformer } = await import('markmap-lib');
        const { Markmap } = await import('markmap-view');

        if (!mounted || !svgRef.current) return;

        // Transform markdown to markmap data
        const transformer = new Transformer();
        const { root } = transformer.transform(content);

        // Create markmap instance
        const mm = Markmap.create(svgRef.current, {
          duration: 500,
          maxWidth: 300,
          paddingX: 20,
          spacingVertical: 10,
          spacingHorizontal: 80,
          autoFit: true,
          color: (node: any) => {
            // Colorful nodes based on depth
            const colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8', '#F7DC6F'];
            const depth = node?.state?.depth ?? 0;
            return colors[depth % colors.length] || '#FF6B6B';
          },
        });

        // Render the markmap
        mm.setData(root);
        mm.fit();

        setError(null);
      } catch (err) {
        if (!mounted) return;
        const message = err instanceof Error ? err.message : 'Failed to render Markmap';
        setError(message);
        console.error('Markmap rendering error:', err);
      }
    };

    void renderMarkmap();

    return () => {
      mounted = false;
    };
  }, [content]);

  if (error) {
    return (
      <div className="flex items-center justify-center h-full p-8">
        <div className="text-red-500 text-center">
          <p className="font-semibold">Failed to render mindmap</p>
          <p className="text-sm mt-2">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full h-full flex items-center justify-center" style={{ minHeight: '400px' }}>
      <svg
        ref={svgRef}
        className="w-full h-full"
        style={{ minHeight: '400px' }}
      />
    </div>
  );
};

export default MarkmapRenderer;
