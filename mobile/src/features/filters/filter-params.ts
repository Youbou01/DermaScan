import type { RiskLevel } from '@/api/types';
import { MAX_INGREDIENTS, clearAll, type FilterState } from './filter-state';

export type RouteParams = Record<string, string | string[] | undefined>;

const RISK_LEVELS: readonly RiskLevel[] = ['low', 'moderate', 'high', 'unknown'];

function first(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}

function decodeScore(value: string | undefined): number | undefined {
  if (value === undefined || value.trim() === '') return undefined;
  const score = Number(value);
  if (!Number.isInteger(score) || score < 0 || score > 100) return undefined;
  return score;
}

function decodeNames(value: string | undefined): string[] {
  if (!value) return [];
  try {
    const parsed: unknown = JSON.parse(value);
    if (!Array.isArray(parsed)) return [];
    const names: string[] = [];
    for (const item of parsed) {
      if (typeof item !== 'string') continue;
      const clean = item.trim();
      const key = clean.toLowerCase();
      if (clean === '' || names.some((name) => name.toLowerCase() === key)) continue;
      names.push(clean);
    }
    return names.slice(0, MAX_INGREDIENTS);
  } catch {
    return [];
  }
}

/** Filter state to route params. Empty filters give no params at all. */
export function encodeFilters(filters: FilterState): Record<string, string> {
  const params: Record<string, string> = {};
  if (filters.category) params.category = filters.category;
  if (filters.bands.length > 0) params.band = filters.bands.join(',');
  if (filters.minScore !== undefined) params.min_score = String(filters.minScore);
  if (filters.maxScore !== undefined) params.max_score = String(filters.maxScore);
  if (filters.include.length > 0) params.include = JSON.stringify(filters.include);
  if (filters.exclude.length > 0) params.exclude = JSON.stringify(filters.exclude);
  return params;
}

/** Route params to filter state. Invalid values are ignored, never thrown. */
export function decodeFilters(params: RouteParams): FilterState {
  const result = clearAll();
  const category = first(params.category)?.trim();
  if (category) result.category = category;
  const parts = (first(params.band) ?? '').split(',');
  result.bands = RISK_LEVELS.filter((level) => parts.includes(level));
  const minScore = decodeScore(first(params.min_score));
  if (minScore !== undefined) result.minScore = minScore;
  const maxScore = decodeScore(first(params.max_score));
  if (maxScore !== undefined) result.maxScore = maxScore;
  result.include = decodeNames(first(params.include));
  result.exclude = decodeNames(first(params.exclude));
  return result;
}
