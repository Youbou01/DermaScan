export function validateReviewInput(rating: number, body: string): string | null {
  if (!Number.isInteger(rating) || rating < 1 || rating > 5) {
    return 'Select a rating between 1 and 5 stars.';
  }
  const trimmed = body.trim();
  if (!trimmed) {
    return 'Write a short comment about your experience.';
  }
  if (trimmed.length > 2000) {
    return 'Review must be 2000 characters or fewer.';
  }
  return null;
}

export function formatReviewDate(isoDate: string): string {
  const parsed = new Date(isoDate);
  if (Number.isNaN(parsed.getTime())) return '';
  return parsed.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}
