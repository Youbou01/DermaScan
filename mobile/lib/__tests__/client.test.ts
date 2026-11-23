import { ApiError, errorMessage, queryString } from '@/lib/api/client';

describe('API Client utilities', () => {
  describe('queryString', () => {
    it('returns empty string for empty object', () => {
      expect(queryString({})).toBe('');
    });

    it('builds query string for scalar values', () => {
      expect(queryString({ q: 'cerave', limit: 10 })).toBe('?q=cerave&limit=10');
    });

    it('ignores undefined, null, and empty string values', () => {
      expect(queryString({ q: 'serum', brand: undefined, category: null, empty: '' })).toBe(
        '?q=serum',
      );
    });

    it('handles array values by repeating the parameter', () => {
      expect(queryString({ bands: ['low', 'moderate'] })).toBe('?bands=low&bands=moderate');
    });

    it('properly URI encodes special characters', () => {
      expect(queryString({ q: 'sun & care' })).toBe('?q=sun%20%26%20care');
    });
  });

  describe('ApiError', () => {
    it('creates an instance with status, message, and error code', () => {
      const err = new ApiError(404, 'Item not found', 'NOT_FOUND');
      expect(err.name).toBe('ApiError');
      expect(err.status).toBe(404);
      expect(err.message).toBe('Item not found');
      expect(err.code).toBe('NOT_FOUND');
    });
  });

  describe('errorMessage', () => {
    it('extracts error message from Error instances', () => {
      expect(errorMessage(new Error('Network failure'))).toBe('Network failure');
    });

    it('returns generic fallback for non-Error values', () => {
      expect(errorMessage('something')).toBe('Something went wrong. Please try again.');
      expect(errorMessage(null)).toBe('Something went wrong. Please try again.');
      expect(errorMessage(undefined)).toBe('Something went wrong. Please try again.');
    });
  });
});
