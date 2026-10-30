import { useQuery, type UseQueryResult } from '@tanstack/react-query';
import { env } from '@/config/env';
import { ApiError } from './errors';
import { apiClient } from './client';
import { findMockSearchResults } from './search-fixture';
import type { CategoryNode, HomeFeed, ProductDetail, ProductIngredient } from './types';

export class ApiContractUnavailableError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'ApiContractUnavailableError';
  }
}

export async function requireData<T>(result: {
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

export function useSearchQuery(
  query: string,
): UseQueryResult<ReturnType<typeof findMockSearchResults>, Error> {
  return useQuery({
    queryKey: ['search', query.trim()],
    enabled: query.trim().length >= 2,
    queryFn: async () => {
      if (env.useMocks) {
        return findMockSearchResults(query);
      }
      throw new ApiContractUnavailableError(
        'Product search is documented as proposed but is not present in the backend OpenAPI schema yet.',
      );
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
