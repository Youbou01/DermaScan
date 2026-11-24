import { queryString } from '@/lib/api/client';
import { formatReviewDate, validateReviewInput } from '@/lib/reviews';

describe('reviews helpers', () => {
  describe('validateReviewInput', () => {
    it('accepts valid rating and non-empty comment', () => {
      expect(validateReviewInput(5, 'Great serum!')).toBeNull();
      expect(validateReviewInput(1, 'Could be better.')).toBeNull();
    });

    it('rejects invalid star ratings', () => {
      expect(validateReviewInput(0, 'Some text')).toBe('Select a rating between 1 and 5 stars.');
      expect(validateReviewInput(6, 'Some text')).toBe('Select a rating between 1 and 5 stars.');
      expect(validateReviewInput(-1, 'Some text')).toBe('Select a rating between 1 and 5 stars.');
      expect(validateReviewInput(3.5, 'Some text')).toBe('Select a rating between 1 and 5 stars.');
    });

    it('rejects empty or whitespace-only bodies', () => {
      expect(validateReviewInput(5, '')).toBe('Write a short comment about your experience.');
      expect(validateReviewInput(5, '   ')).toBe('Write a short comment about your experience.');
      expect(validateReviewInput(5, '\n\t  ')).toBe('Write a short comment about your experience.');
    });

    it('rejects comments exceeding 2000 characters', () => {
      const longComment = 'a'.repeat(2001);
      expect(validateReviewInput(5, longComment)).toBe('Review must be 2000 characters or fewer.');
    });
  });

  describe('queryString', () => {
    it('produces valid query string for sort, direction, and min_score', () => {
      const qs = queryString({ sort: 'rating', direction: 'desc', min_score: 75 });
      expect(qs).toBe('?sort=rating&direction=desc&min_score=75');
    });
  });

  describe('formatReviewDate', () => {
    it('formats a valid ISO timestamp to a date string', () => {
      const formatted = formatReviewDate('2026-11-20T12:00:00Z');
      expect(formatted).toBeTruthy();
      expect(typeof formatted).toBe('string');
      expect(formatted).toContain('2026');
    });

    it('returns empty string for invalid date', () => {
      expect(formatReviewDate('invalid')).toBe('');
      expect(formatReviewDate('')).toBe('');
    });
  });
});
