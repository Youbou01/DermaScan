import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { act, renderHook, waitFor } from '@testing-library/react-native';
import type { PropsWithChildren, ReactElement } from 'react';
import { apiClient } from './client';
import { ApiError } from './errors';
import { useProductListQuery } from './product-list';

jest.mock('@/config/env', () => ({
  env: { apiUrl: 'https://api.test', useMocks: false },
}));
jest.mock('./client', () => ({ apiClient: { GET: jest.fn() } }));

const get = apiClient.GET as unknown as jest.Mock;

const summary = {
  id: 'p1',
  barcode: '3600523956210',
  name: 'Gentle Cleanser',
  brand: 'Demo',
  image_url: null,
  score: 72,
  score_band: 'low',
};

function ok(body: unknown): { data: unknown; response: Response } {
  return { data: body, response: new Response(JSON.stringify(body), { status: 200 }) };
}

function createWrapper(): ({ children }: PropsWithChildren) => ReactElement {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return function QueryWrapper({ children }: PropsWithChildren): ReactElement {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
  };
}

describe('useProductListQuery (real requests)', () => {
  beforeEach(() => {
    get.mockReset();
  });

  it('calls the search endpoint for a query and maps items to product cards', async () => {
    get.mockResolvedValue(ok({ items: [summary], next_cursor: null }));
    const hook = await renderHook(() => useProductListQuery({ query: 'cream' }, 5), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(hook.result.current.isSuccess).toBe(true));

    expect(get).toHaveBeenCalledWith('/api/v1/products/search', {
      params: { query: { q: 'cream', limit: 5 } },
    });
    expect(hook.result.current.data?.pages[0]?.items[0]).toEqual({
      id: 'p1',
      name: 'Gentle Cleanser',
      brand: 'Demo',
      image_url: null,
      score: 72,
      score_band: 'low',
      category_slug: null,
    });
  });

  it('calls the filter endpoint for a category and sends the cursor for the next page', async () => {
    get.mockResolvedValueOnce(ok({ items: [summary], next_cursor: 'abc' }));
    get.mockResolvedValueOnce(ok({ items: [{ ...summary, id: 'p2' }], next_cursor: null }));
    const hook = await renderHook(() => useProductListQuery({ category: 'serum' }, 1), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(hook.result.current.isSuccess).toBe(true));

    expect(get).toHaveBeenNthCalledWith(1, '/api/v1/products/filter', {
      params: { query: { category: 'serum', limit: 1 } },
    });
    expect(hook.result.current.hasNextPage).toBe(true);

    await act(async () => {
      await hook.result.current.fetchNextPage();
    });
    expect(get).toHaveBeenNthCalledWith(2, '/api/v1/products/filter', {
      params: { query: { category: 'serum', limit: 1, cursor: 'abc' } },
    });
    await waitFor(() => expect(hook.result.current.data?.pages).toHaveLength(2));
    await waitFor(() => expect(hook.result.current.hasNextPage).toBe(false));
  });

  it('ignores a query shorter than 2 characters', async () => {
    get.mockResolvedValue(ok({ items: [], next_cursor: null }));
    const hook = await renderHook(() => useProductListQuery({ query: 'a' }), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(hook.result.current.isSuccess).toBe(true));

    expect(get.mock.calls[0]?.[0]).toBe('/api/v1/products/filter');
  });

  it('turns a problem+json response into an ApiError', async () => {
    const problem = { type: 'urn:skincare:problem:internal-error', title: 'Boom', status: 500 };
    get.mockResolvedValue({
      error: problem,
      response: new Response(JSON.stringify(problem), {
        status: 500,
        headers: { 'content-type': 'application/problem+json' },
      }),
    });
    const hook = await renderHook(() => useProductListQuery({}), { wrapper: createWrapper() });
    await waitFor(() => expect(hook.result.current.isError).toBe(true));

    expect(hook.result.current.error).toBeInstanceOf(ApiError);
  });
});
