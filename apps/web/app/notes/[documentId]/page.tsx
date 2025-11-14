'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { Button, Card, Badge } from '@neura/ui';
import { ArrowLeft, Loader2, AlertCircle, FileText, Download } from 'lucide-react';
import { ProtectedRoute } from '@/lib/auth/protected-route';
import { toast } from 'sonner';
import { getNotes, getDocument } from '@/services/api';
import { DocumentMetadata, GetNotesResponse } from '@/lib/types/document';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { getStatusBadgeVariant } from '@/lib/utils/document';

export default function NotesPage() {
  const params = useParams();
  const router = useRouter();
  const documentId = params.documentId as string;

  // State
  const [document, setDocument] = useState<DocumentMetadata | null>(null);
  const [notesData, setNotesData] = useState<GetNotesResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch document and notes data
  const fetchData = async () => {
    setLoading(true);
    setError(null);

    try {
      const results = await Promise.allSettled([
        getDocument(documentId),
        getNotes(documentId),
      ]);

      // Handle document result
      if (results[0].status === 'fulfilled') {
        setDocument(results[0].value);
      }

      // Handle notes result
      if (results[1].status === 'fulfilled') {
        const notesValue = results[1].value;
        // Treat null as empty state (404 - notes not generated)
        if (notesValue === null) {
          setNotesData(null);
          // Do not set error
        } else {
          setNotesData(notesValue);
        }
      } else {
        const err = results[1].reason;
        const errorMessage = err instanceof Error ? err.message : 'Failed to load notes';
        // For non-404 errors, set error message
        setError(errorMessage);
      }
    } finally {
      setLoading(false);
    }
  };

  // Fetch data on mount
  useEffect(() => {
    void fetchData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [documentId]);

  // Download notes handler
  const handleDownloadNotes = () => {
    if (!notesData) return;

    const blob = new Blob([notesData.content], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const link = window.document.createElement('a');
    link.href = url;
    link.download = notesData.filename;
    window.document.body.appendChild(link);
    link.click();
    window.document.body.removeChild(link);
    URL.revokeObjectURL(url);
    toast.success('Notes downloaded');
  };

  // Format file size
  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <ProtectedRoute>
      <main className="min-h-screen p-8 bg-neo-bg text-neo-black">
        {/* Loading State */}
        {loading && (
          <div className="flex items-center justify-center min-h-[60vh]">
            <Card className="bg-neo-white border-2 border-neo-black p-12 text-center">
              <Loader2 className="w-12 h-12 text-neo-main animate-spin mb-4 mx-auto" />
              <p className="text-neo-black/70">Loading notes...</p>
            </Card>
          </div>
        )}

        {/* Error State */}
        {!loading && error && (
          <div className="flex items-center justify-center min-h-[60vh]">
            <Card className="bg-neo-white border-2 border-neo-black p-12 text-center max-w-md">
              <AlertCircle className="w-12 h-12 text-neo-main mb-4 mx-auto" />
              <h2 className="text-xl font-semibold text-neo-black mb-2">Error Loading Notes</h2>
              <p className="text-neo-black/70 mb-6">{error}</p>
              <div className="flex gap-3 justify-center">
                <Button variant="outline" onClick={() => void fetchData()}>
                  Retry
                </Button>
                <Button variant="default" onClick={() => router.push('/dashboard')}>
                  Back to Dashboard
                </Button>
              </div>
            </Card>
          </div>
        )}

        {/* Empty/Not Found State */}
        {!loading && !error && !notesData && (
          <div className="flex items-center justify-center min-h-[60vh]">
            <Card className="bg-neo-white border-2 border-neo-black p-12 text-center max-w-md">
              <FileText className="w-12 h-12 text-neo-main mb-4 mx-auto" />
              <h2 className="text-xl font-semibold text-neo-black mb-2">Notes Not Generated</h2>
              <p className="text-neo-black/70 mb-6">
                Notes have not been generated for this document yet. Go back to the dashboard and click &ldquo;Generate Notes&rdquo; to create them.
              </p>
              <Button variant="default" onClick={() => router.push('/dashboard')}>
                Back to Dashboard
              </Button>
            </Card>
          </div>
        )}

        {/* Main Content */}
        {!loading && !error && notesData && document && (
          <div className="max-w-5xl mx-auto space-y-6">
            {/* Header */}
            <div className="space-y-4">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => router.push('/dashboard')}
                className="text-neo-black/70 hover:text-neo-black"
              >
                <ArrowLeft className="w-4 h-4 mr-2" />
                Back to Dashboard
              </Button>

              <div>
                <h1 className="text-4xl font-bold text-neo-black mb-2">Study Notes</h1>
                <p className="text-lg text-neo-black/70">{document.filename}</p>
              </div>

              {/* Badge row */}
              <div className="flex items-center gap-3">
                <Badge variant={getStatusBadgeVariant(document.status)}>
                  {document.status}
                </Badge>
                <Badge variant="outline" className="text-xs">
                  {formatFileSize(notesData.size_bytes)}
                </Badge>
              </div>
            </div>

            {/* Action Bar */}
            <div className="flex justify-end">
              <Button
                variant="default"
                onClick={handleDownloadNotes}
                className="gap-2"
              >
                <Download className="w-4 h-4" />
                Download Markdown
              </Button>
            </div>

            {/* Notes Content */}
            <Card className="bg-neo-white border-2 border-neo-black p-8">
              <div className="prose prose-invert max-w-none">
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  components={{
                    h1: ({ ...props }) => <h1 className="text-3xl font-bold text-neo-black mb-4 mt-8 first:mt-0" {...props} />,
                    h2: ({ ...props }) => <h2 className="text-2xl font-bold text-neo-black mb-3 mt-6" {...props} />,
                    h3: ({ ...props }) => <h3 className="text-xl font-semibold text-neo-black mb-2 mt-4" {...props} />,
                    h4: ({ ...props }) => <h4 className="text-lg font-semibold text-neo-black mb-2 mt-3" {...props} />,
                    p: ({ ...props }) => <p className="text-neo-black mb-4 leading-relaxed" {...props} />,
                    ul: ({ ...props }) => <ul className="list-disc list-inside text-neo-black mb-4 space-y-2" {...props} />,
                    ol: ({ ...props }) => <ol className="list-decimal list-inside text-neo-black mb-4 space-y-2" {...props} />,
                    li: ({ ...props }) => <li className="text-neo-black" {...props} />,
                    blockquote: ({ ...props }) => (
                      <blockquote className="border-l-4 border-neo-black pl-4 italic text-neo-black/70 mb-4" {...props} />
                    ),
                    code: ({ inline, ...props }: any) =>
                      inline ? (
                        <code className="bg-neo-bg text-neo-black px-1.5 py-0.5 rounded text-sm font-mono" {...props} />
                      ) : (
                        <code className="block bg-neo-bg text-neo-black p-4 rounded-lg text-sm font-mono overflow-x-auto mb-4" {...props} />
                      ),
                    pre: ({ ...props }) => <pre className="mb-4" {...props} />,
                    strong: ({ ...props }) => <strong className="font-bold text-neo-black" {...props} />,
                    em: ({ ...props }) => <em className="italic text-neo-black" {...props} />,
                    a: ({ ...props }) => (
                      <a className="text-neo-main hover:underline" target="_blank" rel="noopener noreferrer" {...props} />
                    ),
                    table: ({ ...props }) => (
                      <div className="overflow-x-auto mb-4">
                        <table className="min-w-full border-2 border-neo-black" {...props} />
                      </div>
                    ),
                    thead: ({ ...props }) => <thead className="bg-neo-bg" {...props} />,
                    tbody: ({ ...props }) => <tbody {...props} />,
                    tr: ({ ...props }) => <tr className="border-b-2 border-neo-black" {...props} />,
                    th: ({ ...props }) => <th className="px-4 py-2 text-left text-neo-black font-semibold" {...props} />,
                    td: ({ ...props }) => <td className="px-4 py-2 text-neo-black" {...props} />,
                    hr: ({ ...props }) => <hr className="border-neo-black my-6" {...props} />,
                  }}
                >
                  {notesData.content}
                </ReactMarkdown>
              </div>
            </Card>
          </div>
        )}
      </main>
    </ProtectedRoute>
  );
}
