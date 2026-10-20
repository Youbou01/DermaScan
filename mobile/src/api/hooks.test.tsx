import { QueryClientProvider } from '@tanstack/react-query';
import { renderHook, waitFor } from '@testing-library/react-native';
import type { PropsWithChildren, ReactElement } from 'react';

import { ApiError } from './errors';
import {
  useCategoriesQuery,
  useHomeQuery,
  useIngredientBreakdownQuery,
  useProductByBarcodeQuery,
  useProductQuery,
  useSearchQuery,
} from './hooks';
import { productFixture } from './fixtures';
import { queryClient } from './query-client';

jest.mock('@/config/env', () => ({
  env: { apiUrl: 'https://mock.invalid', useMocks: true },
}));

function createWrapper(): ({ children }: PropsWithChildren) => ReactElement {
  return function QueryWrapper({ children }: PropsWithChildren): ReactElement {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}

describe('API query hooks', () => {
  beforeEach(() => {
    queryClient.clear();
  });

  afterAll(() => {
    queryClient.clear();
  });

  it('resolves home data, uses its parameterized key, and keeps results fresh for 30 seconds', async () => {
    const result = await renderHook(() => useHomeQuery(5), { wrapper: createWrapper() });

    await waitFor(() => expect(result.result.current.isSuccess).toBe(true));

    expect(result.result.current.data?.sections.map((section) => section.id)).toEqual([
      'categories',
      'top_rated',
      'recently_added',
    ]);
    expect(queryClient.getQueryCache().find({ queryKey: ['home', 5] })).toBeDefined();
    expect(queryClient.getDefaultOptions().queries?.staleTime).toBe(30_000);
    expect(queryClient.getDefaultOptions().queries?.retry).toBe(1);
  });

  it('resolves categories and serves a second observer from the same cached query', async () => {
    const first = await renderHook(() => useCategoriesQuery(), { wrapper: createWrapper() });

    await waitFor(() => expect(first.result.current.isSuccess).toBe(true));
    const cachedQuery = queryClient.getQueryCache().find({ queryKey: ['categories'] });
    expect(first.result.current.data?.[0]?.slug).toBe('face-care');
    expect(cachedQuery?.state.dataUpdateCount).toBe(1);

    const second = await renderHook(() => useCategoriesQuery(), { wrapper: createWrapper() });
    await waitFor(() => expect(second.result.current.isSuccess).toBe(true));

    expect(second.result.current.data).toEqual(first.result.current.data);
    expect(cachedQuery?.state.dataUpdateCount).toBe(1);
  });

  it('resolves product and ingredient breakdown data using their contract keys', async () => {
    const product = await renderHook(() => useProductQuery(productFixture.id), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(product.result.current.isSuccess).toBe(true));

    const byBarcode = await renderHook(() => useProductByBarcodeQuery(productFixture.barcode), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(byBarcode.result.current.isSuccess).toBe(true));

    const ingredients = await renderHook(() => useIngredientBreakdownQuery(productFixture.id), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(ingredients.result.current.isSuccess).toBe(true));

    expect(product.result.current.data?.id).toBe(productFixture.id);
    expect(byBarcode.result.current.data?.barcode).toBe(productFixture.barcode);
    expect(ingredients.result.current.data).toEqual(productFixture.ingredients);
    expect(
      queryClient.getQueryCache().find({ queryKey: ['product', productFixture.id] }),
    ).toBeDefined();
    expect(
      queryClient.getQueryCache().find({
        queryKey: ['product-by-barcode', productFixture.barcode],
      }),
    ).toBeDefined();
    expect(
      queryClient.getQueryCache().find({ queryKey: ['product-ingredients', productFixture.id] }),
    ).toBeDefined();
  });

  it('resolves search from its fixture with a normalized query key', async () => {
    const result = await renderHook(() => useSearchQuery('  serum  '), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.result.current.isSuccess).toBe(true));

    expect(result.result.current.data?.items[0]?.name).toBe('Daily Hydration Serum');
    expect(queryClient.getQueryCache().find({ queryKey: ['search', 'serum'] })).toBeDefined();
  });

  it('returns ApiError instances for problem responses and does not call the network in mock mode', async () => {
    const networkFetch = jest.spyOn(globalThis, 'fetch');
    const result = await renderHook(() => useProductQuery('missing-product'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.result.current.isError).toBe(true), { timeout: 5_000 });

    expect(result.result.current.error).toBeInstanceOf(ApiError);
    expect(result.result.current.error).toMatchObject({
      type: 'urn:skincare:problem:product-not-found',
      status: 404,
      request_id: 'mock-request-0001',
    });
    expect(networkFetch).not.toHaveBeenCalled();
    networkFetch.mockRestore();
  });
});
