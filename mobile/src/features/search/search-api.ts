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
}

export function filterLocalCatalogProducts(params: CatalogFilterParams): ProductCard[] {
  const qNorm = (params.query ?? '').trim().toLowerCase();
  const incNorm = (params.includeIngredient ?? '').trim().toLowerCase();
  const excNorm = (params.excludeIngredient ?? '').trim().toLowerCase();

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
    if (incNorm && incNorm === 'parfum') {
      return product.score_band !== 'low';
    }
    if (excNorm && excNorm === 'parfum' && product.score_band === 'unknown') {
      return false;
    }
    return true;
  });
}

export function useCatalogProductsQuery(
  params: CatalogFilterParams,
): UseQueryResult<ProductCard[], Error> {
  const normalizedKey = {
    query: (params.query ?? '').trim(),
    category: params.category ?? null,
    band: params.band ?? null,
    minScore: params.minScore ?? null,
    include: (params.includeIngredient ?? '').trim(),
    exclude: (params.excludeIngredient ?? '').trim(),
  };

  return useQuery({
    queryKey: ['catalog-products', normalizedKey],
    queryFn: async (): Promise<ProductCard[]> => {
      if (!env.useMocks) {
        try {
          const includeTerms = normalizedKey.include
            .split(',')
            .map((s) => s.trim())
            .filter((s) => s.length >= 2);
          const excludeTerms = normalizedKey.exclude
            .split(',')
            .map((s) => s.trim())
            .filter((s) => s.length >= 2);

          const hasFacetFilters = Boolean(
            normalizedKey.category ||
            normalizedKey.band ||
            normalizedKey.minScore !== null ||
            includeTerms.length > 0 ||
            excludeTerms.length > 0,
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
            for (const term of includeTerms) {
              url.searchParams.append('include', term);
            }
            for (const term of excludeTerms) {
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
