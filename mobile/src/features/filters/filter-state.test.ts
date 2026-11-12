import {
  type FilterState,
  MAX_INGREDIENTS,
  addIngredient,
  clearAll,
  countActiveFilters,
  isScoreRangeValid,
  removeIngredient,
  toggleBand,
} from './filter-state';

describe('filter state', () => {
  it('starts empty', () => {
    expect(countActiveFilters(clearAll())).toBe(0);
  });

  it('toggles a band on and off', () => {
    const on = toggleBand(clearAll(), 'low');
    expect(on.bands).toEqual(['low']);
    expect(toggleBand(on, 'low').bands).toEqual([]);
  });

  it('accepts a valid score range and refuses min above max', () => {
    expect(isScoreRangeValid({ ...clearAll(), minScore: 20, maxScore: 80 })).toBe(true);
    expect(isScoreRangeValid({ ...clearAll(), minScore: 90, maxScore: 10 })).toBe(false);
    expect(isScoreRangeValid({ ...clearAll(), minScore: 90 })).toBe(true);
  });

  it('adds an ingredient trimmed and ignores empty or repeated names', () => {
    const one = addIngredient(clearAll(), 'include', '  Aqua ');
    expect(one.include).toEqual(['Aqua']);
    expect(addIngredient(one, 'include', 'aqua').include).toEqual(['Aqua']);
    expect(addIngredient(one, 'include', '   ')).toBe(one);
  });

  it('moves an ingredient from one list to the other', () => {
    const included = addIngredient(clearAll(), 'include', 'Glycerin');
    const moved = addIngredient(included, 'exclude', 'glycerin');
    expect(moved.include).toEqual([]);
    expect(moved.exclude).toEqual(['glycerin']);
  });

  it('stops at the backend limit of 10 names', () => {
    let state = clearAll();
    for (let i = 0; i < MAX_INGREDIENTS + 2; i += 1) {
      state = addIngredient(state, 'include', `Name ${i}`);
    }
    expect(state.include).toHaveLength(MAX_INGREDIENTS);
  });

  it('removes an ingredient', () => {
    const state = addIngredient(clearAll(), 'exclude', 'Parfum');
    expect(removeIngredient(state, 'exclude', 'Parfum').exclude).toEqual([]);
  });

  it('counts every active filter, with the score range as one', () => {
    const state: FilterState = {
      category: 'serum',
      bands: ['low', 'high'],
      minScore: 10,
      maxScore: 90,
      include: ['Aqua'],
      exclude: ['Parfum'],
    };
    expect(countActiveFilters(state)).toBe(6);
  });

  it('clear all resets everything', () => {
    expect(clearAll()).toEqual({ bands: [], include: [], exclude: [] });
  });
});
