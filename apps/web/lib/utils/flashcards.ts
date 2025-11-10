/**
 * Utility functions for flashcard operations and calculations.
 */

/**
 * Determines if a flashcard is due for review based on its next_review timestamp.
 * Uses ISO string comparison for consistency across the application.
 * 
 * @param nextReviewIso - ISO 8601 timestamp string indicating when the flashcard is next due
 * @returns true if the flashcard is due (next_review is now or in the past), false otherwise
 */
export function isDue(nextReviewIso: string): boolean {
  const nowIso = new Date().toISOString();
  return nextReviewIso <= nowIso;
}

/**
 * Calculates the number of flashcards that are currently due for review.
 * 
 * @param flashcards - Array of flashcard objects with next_review timestamps
 * @returns Count of flashcards that are due
 */
export function calculateDueCount(flashcards: Array<{ next_review: string }>): number {
  return flashcards.filter(fc => isDue(fc.next_review)).length;
}

/**
 * Filters an array of flashcards to only those that are due for review.
 * 
 * @param flashcards - Array of flashcard objects with next_review timestamps
 * @returns Filtered array containing only due flashcards
 */
export function filterDueFlashcards<T extends { next_review: string }>(flashcards: T[]): T[] {
  return flashcards.filter(fc => isDue(fc.next_review));
}
