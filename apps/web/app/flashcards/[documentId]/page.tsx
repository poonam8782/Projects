'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { ProtectedRoute } from '@/lib/auth/protected-route';
import {
  Button,
  Card,
  Badge,
} from '@neura/ui';
import Flashcards from '@/components/Flashcards';
import { DocumentMetadata, FlashcardResponse } from '@/lib/types/document';
import { getDocument, getFlashcardsByDocument } from '@/services/api';
import { ArrowLeft, Loader2, AlertCircle, BookOpen } from 'lucide-react';
import { toast } from 'sonner';
import { getStatusBadgeVariant } from '@/lib/utils/document';
import { filterDueFlashcards } from '@/lib/utils/flashcards';

export default function FlashcardPracticePage() {
  const params = useParams();
  const router = useRouter();
  const documentId = params.documentId as string;

  // State management
  const [document, setDocument] = useState<DocumentMetadata | null>(null);
  const [flashcards, setFlashcards] = useState<FlashcardResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch data function
  const fetchData = async () => {
    setLoading(true);
    setError(null);

    try {
      // Fetch document metadata and flashcards in parallel
      const [doc, cards] = await Promise.all([
        getDocument(documentId),
        getFlashcardsByDocument(documentId),
      ]);

      // Filter to only due flashcards using shared utility
      const dueCards = filterDueFlashcards(cards);

      setDocument(doc);
      setFlashcards(dueCards);
    } catch (err) {
      console.error('Failed to fetch flashcard data:', err);
      const errorMessage = err instanceof Error ? err.message : 'Failed to load flashcards';
      setError(errorMessage);
      toast.error(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  // Fetch on mount
  useEffect(() => {
    fetchData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [documentId]);

  // Navigation handlers
  const handleBackToDashboard = () => {
    router.push('/dashboard');
  };

  const handlePracticeComplete = () => {
    toast.success('Practice session complete!');
    setTimeout(() => router.push('/dashboard'), 2000);
  };

  return (
    <ProtectedRoute>
      <div className="min-h-screen p-8 bg-black-ui">
        {/* Loading state */}
        {loading && (
          <div className="flex items-center justify-center min-h-[60vh]">
            <Card className="bg-surface-ui border-border-ui p-8">
              <div className="flex flex-col items-center gap-4">
                <Loader2 className="w-8 h-8 animate-spin text-text-ui" />
                <p className="text-muted-ui">Loading flashcards...</p>
              </div>
            </Card>
          </div>
        )}

        {/* Error state */}
        {!loading && error && (
          <div className="flex items-center justify-center min-h-[60vh]">
            <Card className="bg-surface-ui border-border-ui p-8 max-w-md">
              <div className="flex flex-col items-center gap-4 text-center">
                <AlertCircle className="w-12 h-12 text-muted-ui" />
                <h2 className="text-xl font-semibold text-text-ui">Error Loading Flashcards</h2>
                <p className="text-muted-ui">{error}</p>
                <div className="flex gap-2 mt-4">
                  <Button onClick={fetchData} variant="outline">
                    Retry
                  </Button>
                  <Button onClick={handleBackToDashboard}>
                    Back to Dashboard
                  </Button>
                </div>
              </div>
            </Card>
          </div>
        )}

        {/* Empty state */}
        {!loading && !error && flashcards.length === 0 && (
          <div className="flex items-center justify-center min-h-[60vh]">
            <Card className="bg-surface-ui border-border-ui p-8 max-w-md">
              <div className="flex flex-col items-center gap-4 text-center">
                <BookOpen className="w-12 h-12 text-muted-ui" />
                <h2 className="text-xl font-semibold text-text-ui">No Flashcards Available</h2>
                <p className="text-muted-ui">
                  Generate flashcards from the dashboard to start practicing
                </p>
                <Button onClick={handleBackToDashboard} className="mt-4">
                  Back to Dashboard
                </Button>
              </div>
            </Card>
          </div>
        )}

        {/* Main content */}
        {!loading && !error && flashcards.length > 0 && (
          <>
            {/* Header section */}
            <header className="space-y-4 mb-8">
              <Button
                variant="ghost"
                onClick={handleBackToDashboard}
                className="hover:bg-surface-ui transition-colors"
                aria-label="Navigate back to dashboard"
              >
                <ArrowLeft className="w-4 h-4 mr-2" />
                Back to Dashboard
              </Button>

              <div>
                <h1 className="text-3xl font-bold text-text-ui">Flashcard Practice</h1>
                {document && (
                  <p className="text-lg text-muted-ui mt-2">{document.filename}</p>
                )}
              </div>

              <div className="flex items-center gap-2">
                <Badge variant="outline" className="text-xs">
                  <BookOpen className="w-3 h-3 mr-1" />
                  {flashcards.length} flashcards
                </Badge>
                {document && (
                  <Badge variant={getStatusBadgeVariant(document.status)}>
                    {document.status}
                  </Badge>
                )}
              </div>
            </header>

            {/* Main content area */}
            <main>
              <Flashcards
                flashcards={flashcards}
                onComplete={handlePracticeComplete}
                className="max-w-3xl mx-auto"
              />
            </main>
          </>
        )}
      </div>
    </ProtectedRoute>
  );
}
