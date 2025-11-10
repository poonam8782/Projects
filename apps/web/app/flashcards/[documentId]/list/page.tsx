'use client';

import { useState, useEffect, useRef } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { Button, Card, CardHeader, CardContent, Badge } from '@neura/ui';
import { ArrowLeft, Loader2, AlertCircle, BookOpen, Play, Calendar, RotateCcw, TrendingUp } from 'lucide-react';
import { ProtectedRoute } from '@/lib/auth/protected-route';
import { toast } from 'sonner';
import { getFlashcardsByDocument, getDocument } from '@/services/api';
import { DocumentMetadata, FlashcardResponse } from '@/lib/types/document';
import { formatDate, formatRelativeTime } from '@/lib/utils/format';
import { getStatusBadgeVariant } from '@/lib/utils/document';
import { calculateDueCount } from '@/lib/utils/flashcards';

type BadgeVariant = 'default' | 'secondary' | 'outline' | 'error' | 'warning' | 'success';

export default function FlashcardListPage() {
  const params = useParams();
  const router = useRouter();
  const documentId = params.documentId as string;

  // State
  const [document, setDocument] = useState<DocumentMetadata | null>(null);
  const [flashcards, setFlashcards] = useState<FlashcardResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Track mounted state to prevent state updates on unmounted component
  const isMountedRef = useRef(true);

  // Fetch document and flashcards data
  const fetchData = async () => {
    setLoading(true);
    setError(null);

    try {
      const [documentData, flashcardsData] = await Promise.all([
        getDocument(documentId),
        getFlashcardsByDocument(documentId),
      ]);

      // Only update state if component is still mounted
      if (isMountedRef.current) {
        setDocument(documentData);
        setFlashcards(flashcardsData); // Show ALL flashcards, no filtering
      }
    } catch (err) {
      console.error('Error fetching flashcards:', err);
      const errorMessage = err instanceof Error ? err.message : 'Failed to load flashcards';
      
      // Only update state if component is still mounted
      if (isMountedRef.current) {
        setError(errorMessage);
        toast.error(errorMessage);
      }
    } finally {
      // Only update state if component is still mounted
      if (isMountedRef.current) {
        setLoading(false);
      }
    }
  };

  // Fetch data on mount and cleanup on unmount
  useEffect(() => {
    isMountedRef.current = true;
    void fetchData();
    
    return () => {
      isMountedRef.current = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [documentId]);

  // Helper: Get due status for a flashcard
  const getDueStatus = (next_review: string): { isDue: boolean; label: string; variant: BadgeVariant } => {
    const nextReviewDate = new Date(next_review);
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const reviewDay = new Date(nextReviewDate.getFullYear(), nextReviewDate.getMonth(), nextReviewDate.getDate());

    if (nextReviewDate <= now) {
      return { isDue: true, label: 'Due Now', variant: 'error' };
    } else if (reviewDay.getTime() === today.getTime()) {
      return { isDue: true, label: 'Due Today', variant: 'warning' };
    } else {
      return { isDue: false, label: 'Scheduled', variant: 'outline' };
    }
  };

  // Helper: Get difficulty label from efactor
  const getEFactorLabel = (efactor: number): string => {
    if (efactor >= 2.5) return 'Easy';
    if (efactor >= 2.0) return 'Medium';
    return 'Hard';
  };

  // Use shared utility for calculating due count
  const dueCount = flashcards.length > 0 ? calculateDueCount(flashcards) : 0;

  // Navigation handlers
  const handleBackToDashboard = () => {
    router.push('/dashboard');
  };

  const handleStartPractice = () => {
    router.push(`/flashcards/${documentId}`);
  };

  return (
    <ProtectedRoute>
      <main className="min-h-screen p-8 bg-black-ui text-text-ui">
        {/* Loading State */}
        {loading && (
          <div className="flex items-center justify-center min-h-[60vh]">
            <Card className="bg-surface-ui border-border-ui p-12 text-center">
              <Loader2 className="w-12 h-12 text-muted-ui animate-spin mb-4 mx-auto" />
              <p className="text-muted-ui">Loading flashcards...</p>
            </Card>
          </div>
        )}

        {/* Error State */}
        {!loading && error && (
          <div className="flex items-center justify-center min-h-[60vh]">
            <Card className="bg-surface-ui border-border-ui p-12 text-center max-w-md">
              <AlertCircle className="w-12 h-12 text-muted-ui mb-4 mx-auto" />
              <h2 className="text-xl font-semibold text-text-ui mb-2">Error Loading Flashcards</h2>
              <p className="text-muted-ui mb-6">{error}</p>
              <div className="flex gap-3 justify-center">
                <Button variant="outline" onClick={() => void fetchData()}>
                  Retry
                </Button>
                <Button variant="default" onClick={handleBackToDashboard}>
                  Back to Dashboard
                </Button>
              </div>
            </Card>
          </div>
        )}

        {/* Empty State */}
        {!loading && !error && flashcards.length === 0 && (
          <div className="flex items-center justify-center min-h-[60vh]">
            <Card className="bg-surface-ui border-border-ui p-12 text-center max-w-md">
              <BookOpen className="w-12 h-12 text-muted-ui mb-4 mx-auto" />
              <h2 className="text-xl font-semibold text-text-ui mb-2">No Flashcards Generated</h2>
              <p className="text-muted-ui mb-6">
                Flashcards have not been generated for this document yet. Go back to the dashboard and click &ldquo;Generate Flashcards&rdquo; to create them.
              </p>
              <Button variant="default" onClick={handleBackToDashboard}>
                Back to Dashboard
              </Button>
            </Card>
          </div>
        )}

        {/* Main Content */}
        {!loading && !error && flashcards.length > 0 && document && (
          <div className="max-w-7xl mx-auto space-y-6">
            {/* Header */}
            <div className="space-y-4">
              <Button
                variant="ghost"
                size="sm"
                onClick={handleBackToDashboard}
                className="text-muted-ui hover:text-text-ui"
                aria-label="Back to Dashboard"
              >
                <ArrowLeft className="w-4 h-4 mr-2" />
                Back to Dashboard
              </Button>

              <div>
                <h1 className="text-4xl font-bold text-text-ui mb-2">Flashcard Library</h1>
                <p className="text-lg text-muted-ui">{document.filename}</p>
              </div>

              {/* Badge row */}
              <div className="flex items-center gap-3 flex-wrap">
                <Badge variant={getStatusBadgeVariant(document.status)}>
                  {document.status}
                </Badge>
                <Badge variant="outline" className="text-xs">
                  {flashcards.length} flashcard{flashcards.length !== 1 ? 's' : ''}
                </Badge>
                {dueCount > 0 && (
                  <Badge variant={dueCount > 5 ? 'error' : 'warning'} className="text-xs">
                    {dueCount} due
                  </Badge>
                )}
              </div>
            </div>

            {/* Action Bar */}
            <div className="flex justify-between items-center gap-3 sticky top-4 z-10 bg-black-ui/95 backdrop-blur-sm p-4 rounded-lg border border-border-ui">
              {dueCount > 0 ? (
                <Button
                  variant="default"
                  onClick={handleStartPractice}
                  className="gap-2"
                  size="lg"
                >
                  <Play className="w-4 h-4" />
                  Start Practice ({dueCount} due)
                </Button>
              ) : (
                <div className="text-sm text-muted-ui">
                  No flashcards due for review right now
                </div>
              )}
              <Button variant="outline" onClick={handleBackToDashboard}>
                Back to Dashboard
              </Button>
            </div>

            {/* Flashcards Grid */}
            <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {flashcards.map((flashcard) => {
                const dueStatus = getDueStatus(flashcard.next_review);
                const difficultyLabel = getEFactorLabel(flashcard.efactor);

                return (
                  <Card
                    key={flashcard.id}
                    className="bg-surface-ui border-border-ui hover:border-primary/50 transition-colors"
                  >
                    <CardHeader className="pb-3">
                      <div className="flex items-center justify-between gap-2 mb-2">
                        <Badge variant={dueStatus.variant} className="text-xs">
                          {dueStatus.label}
                        </Badge>
                        <Badge 
                          variant={
                            flashcard.efactor >= 2.5 
                              ? 'success'  // Easy: green/success color
                              : flashcard.efactor >= 2.0 
                              ? 'outline'  // Medium: neutral outline
                              : 'warning'  // Hard: warning/yellow color
                          } 
                          className="text-xs"
                        >
                          {difficultyLabel}
                        </Badge>
                      </div>
                    </CardHeader>

                    <CardContent className="space-y-4">
                      {/* Question Section */}
                      <div>
                        <div className="text-sm text-muted-ui mb-1">Question</div>
                        <div className="font-semibold text-base text-text-ui">
                          {flashcard.question}
                        </div>
                      </div>

                      {/* Answer Section */}
                      <div>
                        <div className="text-sm text-muted-ui mb-1">Answer</div>
                        <div className="text-base text-text-ui">
                          {flashcard.answer}
                        </div>
                      </div>

                      {/* Metadata Section */}
                      <div className="pt-3 border-t border-border-ui space-y-2 text-xs text-muted-ui">
                        <div className="grid grid-cols-2 gap-2">
                          <div className="flex items-center gap-1">
                            <Calendar className="w-3 h-3" />
                            <span className="truncate" title={formatDate(flashcard.next_review)}>
                              {formatDate(flashcard.next_review)}
                            </span>
                          </div>
                          <div className="flex items-center gap-1">
                            <RotateCcw className="w-3 h-3" />
                            <span>{flashcard.interval} day{flashcard.interval !== 1 ? 's' : ''}</span>
                          </div>
                          <div className="flex items-center gap-1">
                            <TrendingUp className="w-3 h-3" />
                            <span>{flashcard.repetitions} review{flashcard.repetitions !== 1 ? 's' : ''}</span>
                          </div>
                          <div className="flex items-center gap-1">
                            <span className="font-mono">EF: {flashcard.efactor.toFixed(2)}</span>
                          </div>
                        </div>
                        <div className="text-xs">
                          {flashcard.last_reviewed 
                            ? `Last reviewed: ${formatRelativeTime(flashcard.last_reviewed)}`
                            : 'Never reviewed'
                          }
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </section>
          </div>
        )}
      </main>
    </ProtectedRoute>
  );
}
