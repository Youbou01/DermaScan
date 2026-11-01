import type { RiskLevel } from '@/api/types';

export const MAX_INGREDIENTS = 10;

export interface FilterState {
  category?: string;
  bands: RiskLevel[];
  minScore?: number;
  maxScore?: number;
  include: string[];
  exclude: string[];
}

export type IngredientList = 'include' | 'exclude';

export function clearAll(): FilterState {
  return { bands: [], include: [], exclude: [] };
}

export function toggleBand(filters: FilterState, band: RiskLevel): FilterState {
  const bands = filters.bands.includes(band)
    ? filters.bands.filter((item) => item !== band)
    : [...filters.bands, band];
  return { ...filters, bands };
}

export function isScoreRangeValid(filters: FilterState): boolean {
  if (filters.minScore === undefined || filters.maxScore === undefined) return true;
  return filters.minScore <= filters.maxScore;
}

export function addIngredient(
  filters: FilterState,
  list: IngredientList,
  name: string,
): FilterState {
  const clean = name.trim();
  if (clean === '') return filters;
  const other: IngredientList = list === 'include' ? 'exclude' : 'include';
  const key = clean.toLowerCase();
  if (filters[list].some((item) => item.toLowerCase() === key)) return filters;
  if (filters[list].length >= MAX_INGREDIENTS) return filters;
  return {
    ...filters,
    [list]: [...filters[list], clean],
    [other]: filters[other].filter((item) => item.toLowerCase() !== key),
  };
}

export function removeIngredient(
  filters: FilterState,
  list: IngredientList,
  name: string,
): FilterState {
  return { ...filters, [list]: filters[list].filter((item) => item !== name) };
}

export function countActiveFilters(filters: FilterState): number {
  let count = filters.bands.length + filters.include.length + filters.exclude.length;
  if (filters.category) count += 1;
  if (filters.minScore !== undefined || filters.maxScore !== undefined) count += 1;
  return count;
}
