import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { act, renderHook, waitFor } from '@testing-library/react-native';
import type { PropsWithChildren, ReactElement } from 'react';
import { useProductListQuery } from './product-list';

jest.mock('@/config/env', () => ({
  env: { apiUrl: 'https://mock.invalid', useMocks: true },
}));

function createWrapper(): ({ children }: PropsWithChildren) => ReactElement {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return function QueryWrapper({ children }: PropsWithChildren): ReactElement {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
  };
}

describe('useProductListQuery (mock mode)', () => {
  it('loads the first page and then the next one without duplicates', async () => {
    const hook = await renderHook(() => useProductListQuery({}, 1), { wrapper: createWrapper() });
    await waitFor(() => expect(hook.result.current.isSuccess).toBe(true));

    expect(hook.result.current.data?.pages[0]?.items).toHaveLength(1);
    expect(hook.result.current.hasNextPage).toBe(true);

    await act(async () => {
      await hook.result.current.fetchNextPage();
    });
    await waitFor(() => expect(hook.result.current.data?.pages).toHaveLength(2));

    const ids = hook.result.current.data?.pages.flatMap((page) => page.items.map((p) => p.id));
    expect(new Set(ids).size).toBe(ids?.length);
  });

  it('filters by name', async () => {
    const hook = await renderHook(() => useProductListQuery({ query: 'serum' }), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(hook.result.current.isSuccess).toBe(true));

    const items = hook.result.current.data?.pages[0]?.items ?? [];
    expect(items.length).toBeGreaterThan(0);
    expect(items.every((p) => `${p.name} ${p.brand ?? ''}`.toLowerCase().includes('serum'))).toBe(
      true,
    );
  });

  it('filters by category slug', async () => {
    const hook = await renderHook(() => useProductListQuery({ category: 'cleanser' }), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(hook.result.current.isSuccess).toBe(true));

    const items = hook.result.current.data?.pages[0]?.items ?? [];
    expect(items.length).toBeGreaterThan(0);
    expect(items.every((p) => p.category_slug === 'cleanser')).toBe(true);
  });

  it('returns an empty list, without a next page, when nothing matches', async () => {
    const hook = await renderHook(() => useProductListQuery({ query: 'zzzzzzzz' }), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(hook.result.current.isSuccess).toBe(true));

    expect(hook.result.current.data?.pages[0]?.items).toEqual([]);
    expect(hook.result.current.hasNextPage).toBe(false);
  });
});
