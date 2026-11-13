import { useQuery, type UseQueryResult } from '@tanstack/react-query';
import { buildAuthHeaders } from '@/api/auth-token';
import { productCardsFixture } from '@/api/fixtures';
import { getActiveApiLocale } from '@/api/locale';
import type { ProductCard, RiskLevel } from '@/api/types';
import { env } from '@/config/env';

export interface CatalogFilterParams {
  readonly query?: string;
  readonly category?: string | null;
  readonly band?: RiskLevel | null;
  readonly minScore?: number | null;
  readonly includeIngredient?: string;
  readonly excludeIngredient?: string;
  readonly includeIngredients?: readonly string[];
  readonly excludeIngredients?: readonly string[];
}

function normalizeIngredientTerms(single?: string, list?: readonly string[]): string[] {
  const combined: string[] = [];
  for (const item of list ?? []) {
    for (const part of item.split(',')) {
      const trimmed = part.trim();
      if (
        trimmed &&
        !combined.some((existing) => existing.toLowerCase() === trimmed.toLowerCase())
      ) {
        combined.push(trimmed);
      }
    }
  }
  if (single) {
    for (const part of single.split(',')) {
      const trimmed = part.trim();
      if (
        trimmed &&
        !combined.some((existing) => existing.toLowerCase() === trimmed.toLowerCase())
      ) {
        combined.push(trimmed);
      }
    }
  }
  return combined;
}

export function filterLocalCatalogProducts(params: CatalogFilterParams): ProductCard[] {
  const qNorm = (params.query ?? '').trim().toLowerCase();
  const incTerms = normalizeIngredientTerms(
    params.includeIngredient,
    params.includeIngredients,
  ).map((t) => t.toLowerCase());
  const excTerms = normalizeIngredientTerms(
    params.excludeIngredient,
    params.excludeIngredients,
  ).map((t) => t.toLowerCase());

  return productCardsFixture.filter((product) => {
    if (qNorm) {
      const hay =
        `${product.name} ${product.brand ?? ''} ${product.category_slug ?? ''}`.toLowerCase();
      if (!hay.includes(qNorm)) {
        return false;
      }
    }
    if (params.category && product.category_slug !== params.category) {
      return false;
    }
    if (params.band && product.score_band !== params.band) {
      return false;
    }
    if (
      params.minScore !== null &&
      params.minScore !== undefined &&
      (product.score === null || product.score < params.minScore)
    ) {
      return false;
    }
    if (incTerms.includes('parfum') && product.score_band === 'low') {
      return false;
    }
    if (excTerms.includes('parfum') && product.score_band === 'unknown') {
      return false;
    }
    return true;
  });
}

export function useCatalogProductsQuery(
  params: CatalogFilterParams,
): UseQueryResult<ProductCard[], Error> {
  const includeTerms = normalizeIngredientTerms(
    params.includeIngredient,
    params.includeIngredients,
  );
  const excludeTerms = normalizeIngredientTerms(
    params.excludeIngredient,
    params.excludeIngredients,
  );

  const normalizedKey = {
    query: (params.query ?? '').trim(),
    category: params.category ?? null,
    band: params.band ?? null,
    minScore: params.minScore ?? null,
    include: includeTerms,
    exclude: excludeTerms,
  };

  return useQuery({
    queryKey: ['catalog-products', normalizedKey],
    queryFn: async (): Promise<ProductCard[]> => {
      if (!env.useMocks) {
        try {
          const validIncludes = includeTerms.filter((s) => s.length >= 2);
          const validExcludes = excludeTerms.filter((s) => s.length >= 2);

          const hasFacetFilters = Boolean(
            normalizedKey.category ||
            normalizedKey.band ||
            normalizedKey.minScore !== null ||
            validIncludes.length > 0 ||
            validExcludes.length > 0,
          );

          if (normalizedKey.query && !hasFacetFilters) {
            const url = new URL(`${env.apiUrl}/api/v1/products/search`);
            url.searchParams.set('q', normalizedKey.query);
            url.searchParams.set('limit', '50');
            const res = await fetch(url.toString(), {
              headers: buildAuthHeaders({ 'Accept-Language': getActiveApiLocale() }),
            });
            if (res.ok) {
              const page = (await res.json()) as { items?: ProductCard[] };
              return (page.items ?? []).map((item) => ({
                ...item,
                category_slug: item.category_slug ?? null,
                score_is_estimated: item.score_is_estimated ?? false,
              }));
            }
          } else {
            const url = new URL(`${env.apiUrl}/api/v1/products/filter`);
            url.searchParams.set('limit', '50');
            if (normalizedKey.query) {
              url.searchParams.set('q', normalizedKey.query);
            }
            if (normalizedKey.category) {
              url.searchParams.set('category', normalizedKey.category);
            }
            if (normalizedKey.band) {
              url.searchParams.set('band', normalizedKey.band);
            }
            if (normalizedKey.minScore !== null) {
              url.searchParams.set('min_score', String(normalizedKey.minScore));
            }
            for (const term of validIncludes) {
              url.searchParams.append('include', term);
            }
            for (const term of validExcludes) {
              url.searchParams.append('exclude', term);
            }

            const res = await fetch(url.toString(), {
              headers: buildAuthHeaders({ 'Accept-Language': getActiveApiLocale() }),
            });
            if (res.ok) {
              const page = (await res.json()) as { items?: ProductCard[] };
              return (page.items ?? []).map((item) => ({
                ...item,
                category_slug: item.category_slug ?? normalizedKey.category ?? null,
                score_is_estimated: item.score_is_estimated ?? false,
              }));
            }
          }
        } catch {
          // Fall back to deterministic local filter
        }
      }
      return filterLocalCatalogProducts(params);
    },
  });
}
