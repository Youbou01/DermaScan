import { decodeFilters, encodeFilters } from './filter-params';
import { MAX_INGREDIENTS, clearAll, type FilterState } from './filter-state';

describe('filter route params', () => {
  it('gives no params for empty filters', () => {
    expect(encodeFilters(clearAll())).toEqual({});
  });

  it('round-trips every filter', () => {
    const filters: FilterState = {
      category: 'serum',
      bands: ['low', 'high'],
      minScore: 10,
      maxScore: 90,
      include: ['Aqua'],
      exclude: ['Parfum'],
    };
    expect(decodeFilters(encodeFilters(filters))).toEqual(filters);
  });

  it('keeps names that contain a comma', () => {
    const filters: FilterState = { ...clearAll(), include: ['Aqua, Water'] };
    expect(decodeFilters(encodeFilters(filters)).include).toEqual(['Aqua, Water']);
  });

  it('reads the first value when a param is an array', () => {
    expect(decodeFilters({ category: ['serum', 'toner'] }).category).toBe('serum');
  });

  it('ignores unknown bands, bad scores and bad names', () => {
    const decoded = decodeFilters({
      band: 'low,evil,low',
      min_score: '150',
      max_score: 'abc',
      include: 'not json',
      exclude: '[1,"Aqua"," "]',
    });
    expect(decoded.bands).toEqual(['low']);
    expect(decoded.minScore).toBeUndefined();
    expect(decoded.maxScore).toBeUndefined();
    expect(decoded.include).toEqual([]);
    expect(decoded.exclude).toEqual(['Aqua']);
  });

  it('keeps at most 10 names', () => {
    const names = Array.from({ length: MAX_INGREDIENTS + 2 }, (_, i) => `Name ${i}`);
    expect(decodeFilters({ include: JSON.stringify(names) }).include).toHaveLength(MAX_INGREDIENTS);
  });
});
