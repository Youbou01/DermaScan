import {
  useInfiniteQuery,
  type InfiniteData,
  type UseInfiniteQueryResult,
} from '@tanstack/react-query';
import { env } from '@/config/env';
import { apiClient } from './client';
import { requireData } from './hooks';
import { findMockProductPage } from './search-fixture';
import type { ProductCard } from './types';

export const DEFAULT_PAGE_SIZE = 10;
const MIN_QUERY_LENGTH = 2;

export interface ProductListFilters {
  /** Name search. Used when it has at least 2 characters; it wins over `category`. */
  query?: string;
  /** Category slug. Child categories are included by the backend. */
  category?: string;
}

export interface ProductListPage {
  items: ProductCard[];
  next_cursor: string | null;
}

interface ApiProductItem {
  id: string;
  name: string;
  brand: string | null;
  image_url: string | null;
  score: number | null;
  score_band: ProductCard['score_band'];
  category_slug?: string | null;
}

interface ApiProductPage {
  items: ApiProductItem[];
  next_cursor?: string | null;
}

function toCard(item: ApiProductItem): ProductCard {
  return {
    id: item.id,
    name: item.name,
    brand: item.brand,
    image_url: item.image_url,
    score: item.score,
    score_band: item.score_band,
    category_slug: item.category_slug ?? null,
  };
}

function toPage(page: ApiProductPage): ProductListPage {
  return { items: page.items.map(toCard), next_cursor: page.next_cursor ?? null };
}

async function fetchProductPage(
  filters: ProductListFilters,
  cursor: string | undefined,
  pageSize: number,
): Promise<ProductListPage> {
  if (env.useMocks) {
    return findMockProductPage(filters, cursor, pageSize);
  }
  const query = filters.query?.trim() ?? '';
  if (query.length >= MIN_QUERY_LENGTH) {
    return toPage(
      await requireData(
        await apiClient.GET('/api/v1/products/search', {
          params: { query: { q: query, limit: pageSize, cursor } },
        }),
      ),
    );
  }
  return toPage(
    await requireData(
      await apiClient.GET('/api/v1/products/filter', {
        params: { query: { category: filters.category, limit: pageSize, cursor } },
      }),
    ),
  );
}

export function useProductListQuery(
  filters: ProductListFilters,
  pageSize: number = DEFAULT_PAGE_SIZE,
): UseInfiniteQueryResult<InfiniteData<ProductListPage, string | undefined>, Error> {
  const query = filters.query?.trim() ?? '';
  const category = filters.category?.trim() || undefined;
  return useInfiniteQuery({
    queryKey: ['product-list', { query, category }, pageSize],
    initialPageParam: undefined as string | undefined,
    queryFn: ({ pageParam }) => fetchProductPage({ query, category }, pageParam, pageSize),
    getNextPageParam: (lastPage) => lastPage.next_cursor ?? undefined,
  });
}
