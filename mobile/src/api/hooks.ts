import {
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
  type InfiniteData,
  type UseInfiniteQueryResult,
  type UseMutationResult,
  type UseQueryResult,
} from '@tanstack/react-query';
import { env } from '@/config/env';
import { ApiError } from './errors';
import { apiClient } from './client';
import { findMockFilterResults, findMockSearchResults } from './search-fixture';
import { profileFixture, suitabilityFixture } from './fixtures';
import type { ProfileDTO, SuitabilityDTO } from './contracts';
import i18n from '@/i18n/i18n';
import type {
  CategoryNode,
  HomeFeed,
  HomeSection,
  ProductDetail,
  ProductIngredient,
} from './types';
import type { components } from './generated/schema';

export type ProductPage = components['schemas']['Page_ProductSummary_'];
export type ProductSummary = components['schemas']['ProductSummary'];
export interface ProductFilterParams {
  readonly category?: string;
  readonly band?: readonly ('low' | 'moderate' | 'high')[];
  readonly include?: readonly string[];
  readonly exclude?: readonly string[];
}

interface ProductSearchCursor {
  readonly searchCursor: string | null;
  readonly filterCursor: string | null;
}

function parseProductSearchCursor(cursor: string | null): ProductSearchCursor {
  if (!cursor) return { searchCursor: null, filterCursor: null };
  try {
    const value: unknown = JSON.parse(cursor);
    if (
      typeof value === 'object' &&
      value !== null &&
      'searchCursor' in value &&
      'filterCursor' in value &&
      (value.searchCursor === null || typeof value.searchCursor === 'string') &&
      (value.filterCursor === null || typeof value.filterCursor === 'string')
    ) {
      return { searchCursor: value.searchCursor, filterCursor: value.filterCursor };
    }
  } catch {
    /* A malformed local cursor starts from the first page. */
  }
  return { searchCursor: null, filterCursor: null };
}

function packProductSearchCursor(
  searchCursor: string | null,
  filterCursor: string | null,
): string | null {
  return searchCursor || filterCursor ? JSON.stringify({ searchCursor, filterCursor }) : null;
}

let mockProfile: ProfileDTO = profileFixture;

export class ApiContractUnavailableError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'ApiContractUnavailableError';
  }
}

async function requireData<T>(result: {
  data?: T;
  error?: unknown;
  response: Response;
}): Promise<T> {
  if (result.response.ok && result.data !== undefined) {
    return result.data;
  }
  throw await ApiError.fromResponse(result.response, result.error);
}

export function useHomeQuery(limit = 10): UseQueryResult<HomeFeed, ApiError> {
  return useQuery({
    queryKey: ['home', limit],
    queryFn: async () =>
      requireData(await apiClient.GET('/api/v1/home', { params: { query: { limit } } })),
  });
}

export async function fetchHomeSection(
  sectionId: string,
  cursor: string,
  limit = 10,
): Promise<HomeSection> {
  return requireData(
    await apiClient.GET('/api/v1/home/sections/{section_id}', {
      params: { path: { section_id: sectionId }, query: { cursor, limit } },
    }),
  );
}

export function useCategoriesQuery(): UseQueryResult<CategoryNode[], ApiError> {
  return useQuery({
    queryKey: ['categories'],
    queryFn: async () => requireData(await apiClient.GET('/api/v1/categories')),
  });
}

export function useProductQuery(
  productId: string | undefined,
): UseQueryResult<ProductDetail, ApiError> {
  return useQuery({
    queryKey: ['product', productId],
    enabled: Boolean(productId),
    queryFn: async () => {
      if (!productId) {
        throw new Error('A product id is required.');
      }
      return requireData(
        await apiClient.GET('/api/v1/products/{product_id}', {
          params: { path: { product_id: productId } },
        }),
      );
    },
  });
}

export function useProductByBarcodeQuery(
  barcode: string | undefined,
): UseQueryResult<ProductDetail, ApiError> {
  return useQuery({
    queryKey: ['product-by-barcode', barcode],
    enabled: Boolean(barcode),
    queryFn: async () => {
      if (!barcode) {
        throw new Error('A barcode is required.');
      }
      return requireData(
        await apiClient.GET('/api/v1/products/by-barcode/{barcode}', {
          params: { path: { barcode } },
        }),
      );
    },
  });
}

export function useSearchQuery(query: string): UseQueryResult<ProductPage, Error> {
  return useQuery({
    queryKey: ['search', query.trim()],
    enabled: query.trim().length >= 2,
    queryFn: async () => {
      if (env.useMocks) {
        return findMockSearchResults(query);
      }
      return requireData(
        await apiClient.GET('/api/v1/products/search', {
          params: { query: { q: query.trim(), limit: 20 } },
        }),
      );
    },
  });
}

export function useFilterProductsQuery(
  filters: ProductFilterParams,
): UseQueryResult<ProductPage, Error> {
  return useQuery({
    queryKey: ['product-filter', filters],
    queryFn: async () => {
      if (env.useMocks) return findMockFilterResults(filters);
      return requireData(
        await apiClient.GET('/api/v1/products/filter', {
          params: {
            query: {
              category: filters.category,
              band: filters.band ? [...filters.band] : undefined,
              include: filters.include ? [...filters.include] : undefined,
              exclude: filters.exclude ? [...filters.exclude] : undefined,
              limit: 20,
            },
          },
        }),
      );
    },
  });
}

export function useProductSearchInfiniteQuery(
  query: string,
  filters: ProductFilterParams,
): UseInfiniteQueryResult<InfiniteData<ProductPage, ProductSearchCursor>, Error> {
  return useInfiniteQuery({
    queryKey: ['product-search-infinite', query.trim(), filters],
    initialPageParam: { searchCursor: null, filterCursor: null } as ProductSearchCursor,
    enabled:
      query.trim().length >= 2 ||
      Object.values(filters).some((value) => value !== undefined && value.length !== 0),
    queryFn: async ({ pageParam }) => {
      const hasSearch = query.trim().length >= 2;
      const hasFilters = Boolean(
        filters.category ||
        filters.band?.length ||
        filters.include?.length ||
        filters.exclude?.length,
      );
      if (env.useMocks) {
        const searchPage = hasSearch ? findMockSearchResults(query) : null;
        const filterPage = hasFilters ? findMockFilterResults(filters) : null;
        const items =
          searchPage && filterPage
            ? searchPage.items.filter((item) =>
                filterPage.items.some((filtered) => filtered.id === item.id),
              )
            : (searchPage?.items ?? filterPage?.items ?? []);
        return { items, next_cursor: null };
      }
      const filterQuery = {
        category: filters.category,
        band: filters.band ? [...filters.band] : undefined,
        include: filters.include ? [...filters.include] : undefined,
        exclude: filters.exclude ? [...filters.exclude] : undefined,
        limit: 20,
      };
      if (hasSearch && hasFilters) {
        const [searchResult, filterResult] = await Promise.all([
          apiClient.GET('/api/v1/products/search', {
            params: { query: { q: query.trim(), limit: 20, cursor: pageParam.searchCursor } },
          }),
          apiClient.GET('/api/v1/products/filter', {
            params: { query: { ...filterQuery, cursor: pageParam.filterCursor } },
          }),
        ]);
        const [searchPage, filterPage] = await Promise.all([
          requireData(searchResult),
          requireData(filterResult),
        ]);
        const items = searchPage.items.filter((item) =>
          filterPage.items.some((filtered) => filtered.id === item.id),
        );
        return {
          items,
          next_cursor: packProductSearchCursor(searchPage.next_cursor, filterPage.next_cursor),
        };
      }
      if (hasSearch) {
        const result = await requireData(
          await apiClient.GET('/api/v1/products/search', {
            params: { query: { q: query.trim(), limit: 20, cursor: pageParam.searchCursor } },
          }),
        );
        return { ...result, next_cursor: packProductSearchCursor(result.next_cursor, null) };
      }
      const result = await requireData(
        await apiClient.GET('/api/v1/products/filter', {
          params: { query: { ...filterQuery, cursor: pageParam.filterCursor } },
        }),
      );
      return { ...result, next_cursor: packProductSearchCursor(null, result.next_cursor) };
    },
    getNextPageParam: (lastPage) =>
      lastPage.next_cursor ? parseProductSearchCursor(lastPage.next_cursor) : undefined,
  });
}

export function useProfileQuery(userId: string | undefined): UseQueryResult<ProfileDTO, Error> {
  return useQuery({
    queryKey: ['profile', userId],
    enabled: Boolean(userId),
    queryFn: async () => {
      if (!userId) throw new Error('A signed-in user is required.');
      if (!env.useMocks)
        throw new ApiContractUnavailableError(
          'Profile endpoints are not yet present in the backend OpenAPI contract.',
        );
      return { ...mockProfile, user_id: userId };
    },
  });
}

export function useUpdateProfileMutation(
  userId: string | undefined,
): UseMutationResult<ProfileDTO, Error, ProfileDTO> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (next: ProfileDTO): Promise<ProfileDTO> => {
      if (!userId) throw new Error('A signed-in user is required.');
      if (!env.useMocks)
        throw new ApiContractUnavailableError(
          'Profile endpoints are not yet present in the backend OpenAPI contract.',
        );
      mockProfile = next;
      return next;
    },
    onMutate: async (next) => {
      await queryClient.cancelQueries({ queryKey: ['profile', userId] });
      const previous = queryClient.getQueryData<ProfileDTO>(['profile', userId]);
      queryClient.setQueryData(['profile', userId], next);
      return { previous };
    },
    onError: (_error, _next, context) => {
      if (context?.previous) queryClient.setQueryData(['profile', userId], context.previous);
    },
    onSettled: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['profile'] }),
        queryClient.invalidateQueries({ queryKey: ['product-suitability'] }),
      ]);
    },
  });
}

export function useProductSuitabilityQuery(
  productId: string | undefined,
  userId: string | undefined,
): UseQueryResult<SuitabilityDTO, Error> {
  return useQuery({
    queryKey: ['product-suitability', productId, userId],
    enabled: Boolean(productId && userId),
    queryFn: async () => {
      if (!productId || !userId) throw new Error('Product and signed-in user are required.');
      if (!env.useMocks)
        throw new ApiContractUnavailableError(
          'Product suitability is not yet present in the backend OpenAPI contract.',
        );
      const blacklisted = mockProfile.blacklisted_product_ids.includes(productId);
      return {
        ...suitabilityFixture,
        product_id: productId,
        is_blacklisted: blacklisted,
        suits_profile: !blacklisted,
        verdict: blacklisted ? 'avoid' : 'suitable',
        has_risk_alert: blacklisted,
        alerts: blacklisted
          ? [
              {
                code: 'blacklisted',
                severity: 'high',
                ingredient_name: null,
                title: i18n.t('suitability.risk_alert'),
                detail: i18n.t('suitability.blacklisted'),
              },
            ]
          : [],
      };
    },
  });
}

export function useIngredientBreakdownQuery(
  productId: string | undefined,
): UseQueryResult<ProductIngredient[], ApiError> {
  return useQuery({
    queryKey: ['product-ingredients', productId],
    enabled: Boolean(productId),
    queryFn: async () => {
      if (!productId) {
        throw new Error('A product id is required.');
      }
      const product = await requireData(
        await apiClient.GET('/api/v1/products/{product_id}', {
          params: { path: { product_id: productId } },
        }),
      );
      return product.ingredients;
    },
  });
}
