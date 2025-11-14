'use client';

import React, { useEffect, useRef, useState, useCallback } from 'react';
import DOMPurify from 'isomorphic-dompurify';
import { TransformWrapper, TransformComponent, ReactZoomPanPinchRef } from 'react-zoom-pan-pinch';
import { Button, Card, CardContent } from '@neura/ui';
import { generateMindmap } from '@/services/api';
import dynamic from 'next/dynamic';

// Dynamically import mermaid to avoid SSR issues
const Mermaid = dynamic(() => import('./renderers/MermaidRenderer'), { ssr: false });
const Markmap = dynamic(() => import('./renderers/MarkmapRenderer'), { ssr: false });

interface MindmapViewerUnifiedProps {
  content?: string;
  downloadUrl?: string;
  documentId?: string;
  documentName?: string;
  format?: 'svg' | 'mermaid' | 'markmap';
  className?: string;
  showControls?: boolean;
  allowFullscreen?: boolean;
  onError?: (error: string) => void;
  bare?: boolean;
}

export const MindmapViewerUnified: React.FC<MindmapViewerUnifiedProps> = ({
  content: initialContent,
  downloadUrl,
  documentId,
  documentName,
  format = 'mermaid',
  className,
  showControls = true,
  allowFullscreen = true,
  onError,
  bare = false,
}) => {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const zoomRef = useRef<ReactZoomPanPinchRef | null>(null);
  const [mindmapContent, setMindmapContent] = useState<string>('');
  const [mindmapFormat, setMindmapFormat] = useState<'svg' | 'mermaid' | 'markmap'>(format);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [isFullscreen, setIsFullscreen] = useState<boolean>(false);
  const [nodeCount, setNodeCount] = useState<number | null>(null);

  const sanitizeSvg = useCallback((raw: string): string => {
    const cleaned = DOMPurify.sanitize(raw, {
      USE_PROFILES: { svg: true, svgFilters: true },
      ADD_TAGS: [
        'svg','g','defs','use','rect','circle','ellipse','line','path','polyline','polygon','text','tspan',
        'image','mask','pattern','linearGradient','radialGradient','stop','clipPath','filter','feGaussianBlur','title','desc'
      ],
      FORBID_TAGS: ['script','iframe','object','embed','foreignObject'],
      FORBID_ATTR: [
        'onload','onerror','onclick','onmouseover','onmouseenter','onmouseleave','onfocus','onblur','onmousemove','onkeydown','onkeyup','onkeypress'
      ],
      ADD_ATTR: ['viewBox','preserveAspectRatio','role','aria-hidden'],
    });
    return cleaned;
  }, []);

  const normalizeSvg = useCallback((raw: string): string => {
    if (!raw) return raw;
    return raw.replace(/<svg([^>]*)>/i, (match, attrs) => {
      let a = attrs || '';
      a = a.replace(/\b(width|height)=["'][^"']*["']/gi, '');
      if (!/preserveAspectRatio=/i.test(a)) a += ' preserveAspectRatio="xMidYMid meet"';
      if (!/\brole=/i.test(a)) a += ' role="img"';
      if (!/\bfocusable=/i.test(a)) a += ' focusable="false"';
      if (!/style=/i.test(a)) a += ' style="max-width:100%;height:auto;display:block"';
      return `<svg${a}>`;
    });
  }, []);

  const computeNodeCount = useCallback((raw: string, fmt: string): number => {
    if (fmt === 'svg') {
      const matches = raw.match(/<(circle|rect|ellipse|text|path)\b/gi);
      return matches ? matches.length : 0;
    } else if (fmt === 'mermaid') {
      const lines = raw.split('\n').filter(l => l.trim() && !l.trim().startsWith('mindmap'));
      return lines.length;
    } else { // markmap
      const matches = raw.match(/^#{1,6}\s+/gm);
      return matches ? matches.length : 0;
    }
  }, []);

  const loadAndProcess = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      let raw = '';
      let fmt = mindmapFormat;

      if (initialContent) {
        raw = initialContent;
      } else if (downloadUrl) {
        const resp = await fetch(downloadUrl);
        if (!resp.ok) throw new Error(`Failed to fetch mindmap: ${resp.status}`);
        raw = await resp.text();
      } else if (documentId) {
        const gen = await generateMindmap(documentId, mindmapFormat);
        if (!gen.download_url) throw new Error('Missing download URL after generation');
        fmt = gen.format;
        setMindmapFormat(fmt);
        const resp = await fetch(gen.download_url);
        if (!resp.ok) throw new Error(`Failed to fetch generated mindmap: ${resp.status}`);
        raw = await resp.text();
      } else {
        setMindmapContent('');
        setNodeCount(null);
        return;
      }

      // Process based on format
      let processed = raw;
      if (fmt === 'svg') {
        processed = normalizeSvg(sanitizeSvg(raw));
      }

      setMindmapContent(processed);
      setNodeCount(computeNodeCount(processed, fmt));

      if (fmt === 'svg') {
        requestAnimationFrame(() => {
          zoomRef.current?.resetTransform?.();
          zoomRef.current?.centerView?.();
        });
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Failed to load mindmap';
      setError(msg);
      onError?.(msg);
    } finally {
      setLoading(false);
    }
  }, [initialContent, downloadUrl, documentId, mindmapFormat, sanitizeSvg, normalizeSvg, computeNodeCount, onError]);

  useEffect(() => {
    void loadAndProcess();
  }, [loadAndProcess]);

  useEffect(() => {
    const handler = () => setIsFullscreen(!!document.fullscreenElement);
    document.addEventListener('fullscreenchange', handler);
    return () => document.removeEventListener('fullscreenchange', handler);
  }, []);

  const handleDownload = useCallback(() => {
    try {
      const fileExtension = mindmapFormat === 'svg' ? 'svg' : mindmapFormat === 'mermaid' ? 'mmd' : 'md';
      const mimeType = mindmapFormat === 'svg' ? 'image/svg+xml' :
                        mindmapFormat === 'mermaid' ? 'text/plain' : 'text/markdown';

      const blob = new Blob([mindmapContent], { type: mimeType });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${documentName || 'mindmap'}.${fileExtension}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Download failed';
      setError(msg);
      onError?.(msg);
    }
  }, [mindmapContent, mindmapFormat, documentName, onError]);

  const toggleFullscreen = useCallback(() => {
    if (!allowFullscreen) return;
    try {
      if (!isFullscreen) {
        containerRef.current?.requestFullscreen();
      } else {
        document.exitFullscreen();
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Fullscreen toggle failed';
      setError(msg);
      onError?.(msg);
    }
  }, [allowFullscreen, isFullscreen, onError]);

  const handleZoomIn = useCallback(() => zoomRef.current?.zoomIn?.(), []);
  const handleZoomOut = useCallback(() => zoomRef.current?.zoomOut?.(), []);
  const handleResetTransform = useCallback(() => {
    zoomRef.current?.resetTransform?.();
    zoomRef.current?.centerView?.();
  }, []);
  const handleCenterView = useCallback(() => zoomRef.current?.centerView?.(), []);

  const handleFormatChange = useCallback((newFormat: 'svg' | 'mermaid' | 'markmap') => {
    setMindmapFormat(newFormat);
    setMindmapContent('');
    setNodeCount(null);
  }, []);

  const header = (
    <div className="p-4 flex flex-row items-center justify-between">
      <div className="flex flex-col gap-2">
        <div className="text-base font-medium flex items-center gap-2">
          {documentName || 'Mindmap'}
          {nodeCount !== null && nodeCount > 0 && (
            <span className="inline-block text-xs px-2 py-1 rounded bg-neutral-800 border border-neutral-700" aria-label="Node count">
              {nodeCount} nodes
            </span>
          )}
          <span className="inline-block text-xs px-2 py-1 rounded bg-blue-900 border border-blue-700">
            {mindmapFormat.toUpperCase()}
          </span>
        </div>
        {loading && <span className="text-xs text-neutral-400">Loading...</span>}
        {error && <span className="text-xs text-red-500" role="alert">{error}</span>}

        {/* Format selector */}
        {documentId && !loading && (
          <div className="flex gap-2">
            <Button
              variant={mindmapFormat === 'mermaid' ? 'default' : 'outline'}
              size="sm"
              onClick={() => handleFormatChange('mermaid')}
            >
              Mermaid
            </Button>
            <Button
              variant={mindmapFormat === 'markmap' ? 'default' : 'outline'}
              size="sm"
              onClick={() => handleFormatChange('markmap')}
            >
              Markmap
            </Button>
            <Button
              variant={mindmapFormat === 'svg' ? 'default' : 'outline'}
              size="sm"
              onClick={() => handleFormatChange('svg')}
            >
              SVG
            </Button>
          </div>
        )}
      </div>
      {showControls && (
        <div className="flex items-center gap-2">
          {mindmapFormat === 'svg' && (
            <>
              <Button variant="ghost" size="sm" aria-label="Zoom in" onClick={handleZoomIn}>+</Button>
              <Button variant="ghost" size="sm" aria-label="Zoom out" onClick={handleZoomOut}>−</Button>
              <Button variant="ghost" size="sm" aria-label="Reset zoom" onClick={handleResetTransform}>Reset</Button>
              <Button variant="ghost" size="sm" aria-label="Center view" onClick={handleCenterView}>Center</Button>
            </>
          )}
          <Button variant="ghost" size="sm" aria-label="Download" onClick={handleDownload}>Download</Button>
          {documentId && (
            <Button variant="ghost" size="sm" aria-label="Open standalone" onClick={() => window.open(`/mindmap/${documentId}`, '_blank')}>Open</Button>
          )}
          {allowFullscreen && (
            <Button variant="ghost" size="sm" aria-label={isFullscreen ? 'Exit fullscreen' : 'Enter fullscreen'} onClick={toggleFullscreen}>
              {isFullscreen ? 'Exit' : 'Full'}
            </Button>
          )}
        </div>
      )}
    </div>
  );

  const renderContent = () => {
    if (loading) {
      return <div className="text-gray-500 text-center p-8">Loading mindmap...</div>;
    }

    if (error) {
      return <div className="text-red-500 text-center p-8">{error}</div>;
    }

    if (!mindmapContent) {
      return <div className="text-gray-400 text-center p-8">No mindmap available</div>;
    }

    if (mindmapFormat === 'svg') {
      return (
        <TransformWrapper
          onInit={(ref) => { zoomRef.current = ref; }}
          minScale={0.1}
          maxScale={5}
          initialScale={1}
          wheel={{ step: 0.12 }}
          doubleClick={{ mode: 'zoomIn' }}
          panning={{ disabled: false }}
          centerOnInit={true}
        >
          <TransformComponent wrapperClass="w-full h-full" contentClass="w-full h-full flex items-center justify-center">
            <div
              className="inline-block"
              style={{ width: 'auto', height: 'auto', maxWidth: '100%', maxHeight: '100%' }}
              dangerouslySetInnerHTML={{ __html: mindmapContent }}
            />
          </TransformComponent>
        </TransformWrapper>
      );
    }

    if (mindmapFormat === 'mermaid') {
      return <Mermaid content={mindmapContent} />;
    }

    if (mindmapFormat === 'markmap') {
      return <Markmap content={mindmapContent} />;
    }

    return null;
  };

  const content = (
    <div className={`p-0 ${isFullscreen ? 'h-[calc(100vh-64px)]' : bare ? 'h-[calc(100vh-64px)]' : 'h-[600px]'}`}>
      <div ref={containerRef} className="w-full h-full bg-white overflow-auto">
        {renderContent()}
      </div>
    </div>
  );

  if (bare) {
    return (
      <div className={`relative w-full h-full ${isFullscreen ? 'fixed inset-0 z-50' : ''} ${className || ''}`}>
        {header}
        {content}
      </div>
    );
  }

  return (
    <Card className={`border-border-ui bg-surface-ui text-text-ui ${className || ''} ${isFullscreen ? 'fixed inset-0 z-50 rounded-none' : ''}`}>
      {header}
      <CardContent className="p-0">
        {content}
      </CardContent>
    </Card>
  );
};

export default MindmapViewerUnified;
