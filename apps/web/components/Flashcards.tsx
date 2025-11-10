'use client';

/**
 * Flashcards Component
 * 
 * Practice flashcards with 3D flip animation and SM-2 spaced repetition.
 * Displays question/answer cards with click-to-reveal interaction and quality rating buttons.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Button } from '@neura/ui';
import { Card, CardHeader, CardTitle, CardContent } from '@neura/ui';
import { cn } from '@/lib/utils';
import { formatDate } from '@/lib/utils/format';
import { RotateCcw, Loader2, CheckCircle, AlertCircle, ChevronRight } from 'lucide-react';
import { reviewFlashcard } from '@/services/api';
import type { FlashcardResponse } from '@/lib/types/document';
import { toast } from 'sonner';

interface FlashcardsProps {
  flashcards: FlashcardResponse[];
  onComplete?: () => void;
  onReviewComplete?: (flashcard: FlashcardResponse, quality: number) => void;
  className?: string;
}

export default function Flashcards({ 
  flashcards, 
  onComplete, 
  onReviewComplete,
  className 
}: FlashcardsProps) {
  // State management
  const [currentFlashcard, setCurrentFlashcard] = useState<FlashcardResponse | null>(null);
  const [isFlipped, setIsFlipped] = useState(false);
  const [isReviewing, setIsReviewing] = useState(false);
  const [reviewedCount, setReviewedCount] = useState(0);
  const [dueCount, setDueCount] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [sessionComplete, setSessionComplete] = useState(false);

  // Refs
  const flashcardQueueRef = useRef<FlashcardResponse[]>([]);

  // Initialize flashcard queue on mount
  useEffect(() => {
    flashcardQueueRef.current = flashcards;
    setCurrentFlashcard(flashcards[0] || null);
    setDueCount(flashcards.length);
    
    // Detect empty queue and set session complete
    if (flashcards.length === 0) {
      setSessionComplete(true);
    }
  }, [flashcards]);

  // Handle card flip
  const handleFlipCard = useCallback(() => {
    setIsFlipped(prev => !prev);
  }, []);

  // Handle keyboard navigation
  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === ' ' || e.key === 'Enter') {
      e.preventDefault();
      handleFlipCard();
    }
  }, [handleFlipCard]);

  // Handle quality rating submission
  const handleRating = useCallback(async (quality: number) => {
    if (!currentFlashcard) return;
    
    // Guard against rapid double-submissions
    if (isReviewing) return;

    // Validate quality range
    if (quality < 0 || quality > 5) {
      toast.error('Invalid quality rating. Must be between 0 and 5.');
      return;
    }

    setIsReviewing(true);
    setError(null);
    const loadingToast = toast.loading('Updating schedule...');

    try {
      const result = await reviewFlashcard(currentFlashcard.id, quality);

      // Dismiss loading toast
      toast.dismiss(loadingToast);
      
      // Show success toast with interval message
      toast.success(result.message);

      // Increment reviewed count
      setReviewedCount(prev => prev + 1);

      // Update due count from response
      setDueCount(result.due_count);

      // Call onReviewComplete callback if provided
      if (onReviewComplete) {
        onReviewComplete(result.reviewed_flashcard, quality);
      }

      // Check if there's a next flashcard
      if (result.next_flashcard) {
        // Set next flashcard
        setCurrentFlashcard(result.next_flashcard);
        
        // Reset flip state to show question
        setIsFlipped(false);

        // Update queue (remove reviewed, add next)
        flashcardQueueRef.current = flashcardQueueRef.current.slice(1);
        flashcardQueueRef.current.push(result.next_flashcard);
      } else {
        // No more flashcards - session complete
        setSessionComplete(true);
        setCurrentFlashcard(null);
        toast.success('All flashcards reviewed!');
        
        // Call onComplete callback if provided
        if (onComplete) {
          onComplete();
        }
      }
    } catch (err) {
      toast.dismiss(loadingToast);
      const errorMessage = err instanceof Error ? err.message : 'Failed to review flashcard';
      toast.error(errorMessage);
      setError(errorMessage);
      console.error('Review error:', err);
    } finally {
      setIsReviewing(false);
    }
  }, [currentFlashcard, onComplete, onReviewComplete, isReviewing]);

  // Handle session restart
  const handleRestart = useCallback(() => {
    setReviewedCount(0);
    setSessionComplete(false);
    setIsFlipped(false);
    setError(null);
    setCurrentFlashcard(flashcards[0] || null);
    setDueCount(flashcards.length);
    flashcardQueueRef.current = flashcards;
  }, [flashcards]);

  // Calculate progress percentage
  const progressPercentage = dueCount > 0 
    ? Math.round((reviewedCount / (reviewedCount + dueCount)) * 100) 
    : 100;

  return (
    <Card className={cn('p-6', className)}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <ChevronRight className="w-5 h-5" />
          Flashcard Practice
        </CardTitle>

        {/* Progress indicators */}
        <div className="mt-4 space-y-2">
          <div className="flex items-center justify-between text-sm text-muted-foreground">
            <span>{reviewedCount} reviewed • {dueCount} remaining</span>
            <span>{progressPercentage}%</span>
          </div>

          {/* Progress bar */}
          <div className="w-full h-2 bg-muted border border-border rounded-full overflow-hidden">
            <motion.div
              className="h-full bg-primary"
              initial={{ width: 0 }}
              animate={{ width: `${progressPercentage}%` }}
              transition={{ duration: 0.3, ease: 'easeOut' }}
            />
          </div>
        </div>
      </CardHeader>

      <CardContent className="mt-6">
        <AnimatePresence mode="wait">
          {/* Loading state */}
          {!currentFlashcard && !sessionComplete && (
            <motion.div
              key="loading"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="flex flex-col items-center justify-center py-12 text-muted-foreground"
            >
              <Loader2 className="w-8 h-8 animate-spin mb-4" />
              <p>Loading flashcard...</p>
            </motion.div>
          )}

          {/* Session complete state */}
          {sessionComplete && (
            <motion.div
              key="complete"
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.8, opacity: 0 }}
              transition={{ duration: 0.3 }}
              className="flex flex-col items-center justify-center py-12 space-y-6"
            >
              <CheckCircle className="w-16 h-16 text-primary" />
              <div className="text-center space-y-2">
                <h3 className="text-xl font-semibold">
                  {reviewedCount === 0 ? 'No flashcards due right now' : 'All flashcards reviewed!'}
                </h3>
                <p className="text-muted-foreground">
                  {reviewedCount === 0
                    ? 'Check back later or generate flashcards from a document'
                    : `${reviewedCount} flashcards reviewed`}
                </p>
              </div>
              <Button
                onClick={handleRestart}
                variant="outline"
              >
                <RotateCcw className="w-4 h-4 mr-2" />
                Restart Practice
              </Button>
            </motion.div>
          )}

          {/* Flashcard display */}
          {currentFlashcard && !sessionComplete && (
            <motion.div
              key={currentFlashcard.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.3 }}
              className="space-y-6"
            >
              {/* 3D Flip Card */}
              <div 
                className="relative w-full min-h-[300px]"
                style={{ perspective: '1000px' }}
              >
                <motion.div
                  className="relative w-full h-full"
                  style={{ transformStyle: 'preserve-3d' }}
                  animate={{ rotateY: isFlipped ? 180 : 0 }}
                  transition={{ duration: 0.6, ease: 'easeInOut' }}
                >
                  {/* Front side - Question */}
                  <div
                    className="absolute inset-0 bg-card border-2 border-border rounded-lg p-8 min-h-[300px] flex flex-col items-center justify-center cursor-pointer"
                    style={{
                      backfaceVisibility: 'hidden',
                      transform: 'rotateY(0deg)'
                    }}
                    onClick={handleFlipCard}
                    onKeyDown={handleKeyDown}
                    role="button"
                    tabIndex={0}
                    aria-label="Flashcard - Click to reveal answer"
                  >
                    <div className="text-center space-y-4">
                      <p className="text-xl font-semibold text-card-foreground">
                        {currentFlashcard.question}
                      </p>
                      <p className="text-sm text-muted-foreground">Click to reveal answer</p>
                    </div>
                  </div>

                  {/* Back side - Answer */}
                  <div
                    className="absolute inset-0 bg-card border-2 border-border rounded-lg p-8 min-h-[300px] flex flex-col items-center justify-center cursor-pointer"
                    style={{
                      backfaceVisibility: 'hidden',
                      transform: 'rotateY(180deg)'
                    }}
                    onClick={handleFlipCard}
                    onKeyDown={handleKeyDown}
                    role="button"
                    tabIndex={0}
                    aria-label="Flashcard answer - Click to flip back to question"
                  >
                    <div className="text-center space-y-4 w-full">
                      <p className="text-lg text-card-foreground">
                        {currentFlashcard.answer}
                      </p>
                      <p className="text-sm text-muted-foreground">Rate your recall</p>
                    </div>
                  </div>
                </motion.div>
              </div>

              {/* Rating buttons - only shown when flipped */}
              <AnimatePresence>
                {isFlipped && (
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: 10 }}
                    transition={{ duration: 0.3, delay: 0.3 }}
                    className="space-y-4"
                  >
                    <div className="flex items-center justify-center gap-2 flex-wrap">
                      {[
                        { quality: 1, label: 'Hard' },
                        { quality: 2, label: 'Difficult' },
                        { quality: 3, label: 'Good' },
                        { quality: 4, label: 'Easy' },
                        { quality: 5, label: 'Perfect' },
                      ].map(({ quality, label }) => (
                        <Button
                          key={quality}
                          onClick={() => handleRating(quality)}
                          disabled={isReviewing}
                          variant="outline"
                          size="sm"
                          className="min-w-[80px]"
                        >
                          {isReviewing ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                          ) : (
                            <span className="flex flex-col items-center">
                              <span className="font-semibold">{quality}</span>
                              <span className="text-xs text-muted-foreground">{label}</span>
                            </span>
                          )}
                        </Button>
                      ))}
                    </div>

                    {/* Metadata section */}
                    <div className="text-xs text-muted-foreground space-y-1 text-center">
                      <p>Current interval: {currentFlashcard.interval} day{currentFlashcard.interval !== 1 ? 's' : ''}</p>
                      <p>Next review: {formatDate(currentFlashcard.next_review)}</p>
                      <p>Successful reviews: {currentFlashcard.repetitions}</p>
                      <p>Easiness: {currentFlashcard.efactor.toFixed(2)}</p>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>

              {/* Error state */}
              {error && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="flex items-center gap-2 p-4 bg-destructive/10 border border-destructive/20 rounded-lg text-destructive"
                >
                  <AlertCircle className="w-4 h-4 flex-shrink-0" />
                  <p className="text-sm">{error}</p>
                  <Button
                    onClick={() => setError(null)}
                    variant="outline"
                    size="sm"
                    className="ml-auto"
                  >
                    Dismiss
                  </Button>
                </motion.div>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </CardContent>
    </Card>
  );
}
