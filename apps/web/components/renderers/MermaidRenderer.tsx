'use client';

import React, { useEffect, useRef, useState } from 'react';

interface MermaidRendererProps {
  content: string;
}

const MermaidRenderer: React.FC<MermaidRendererProps> = ({ content }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!content || !containerRef.current) return;

    let mounted = true;

    const renderMermaid = async () => {
      try {
        const mermaid = (await import('mermaid')).default;

        // Configure mermaid
        mermaid.initialize({
          startOnLoad: false,
          theme: 'default',
          securityLevel: 'strict',
          mindmap: {
            padding: 50,
            useMaxWidth: true,
          },
        });

        if (!mounted || !containerRef.current) return;

        // Clear previous content
        containerRef.current.innerHTML = '';

        // Generate unique ID for this render
        const id = `mermaid-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

        // Render the diagram
        const { svg } = await mermaid.render(id, content);

        if (!mounted || !containerRef.current) return;

        containerRef.current.innerHTML = svg;
        setError(null);
      } catch (err) {
        if (!mounted) return;
        const message = err instanceof Error ? err.message : 'Failed to render Mermaid diagram';
        setError(message);
        console.error('Mermaid rendering error:', err);
      }
    };

    void renderMermaid();

    return () => {
      mounted = false;
    };
  }, [content]);

  if (error) {
    return (
      <div className="flex items-center justify-center h-full p-8 bg-white">
        <div className="text-red-600 text-center max-w-2xl">
          <p className="font-semibold text-lg mb-3">Failed to render Mermaid mindmap</p>
          <p className="text-sm mt-2 text-gray-700 bg-red-50 p-4 rounded border border-red-200 font-mono text-left overflow-auto">
            {error}
          </p>
          <p className="text-xs mt-4 text-gray-500">
            Try switching to <strong>Markmap</strong> or <strong>SVG</strong> format using the buttons above.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className="w-full h-full flex items-center justify-center overflow-auto p-4"
      style={{ minHeight: '400px' }}
    />
  );
};

export default MermaidRenderer;
