import type { ReactElement } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, waitFor } from '@testing-library/react-native';
import type { UseQueryResult } from '@tanstack/react-query';
import { fetchHomeSection } from '@/api/hooks';
import { homeFixture, productCardsFixture } from '@/api/fixtures';
import type { HomeFeed } from '@/api/types';
import i18n from '@/i18n/i18n';
import { LanguageProvider } from '@/i18n/LanguageProvider';
import HomeRoute from '@/app/index';
import { refreshHomeFeed } from '@/features/home/HomeScreen';

const mockPush = jest.fn();
let mockQueryResult: UseQueryResult<HomeFeed>;

jest.mock('expo-router', () => ({
  useRouter: () => ({ push: mockPush }),
}));

jest.mock('@/api/hooks', () => ({
  useHomeQuery: () => mockQueryResult,
  fetchHomeSection: jest.fn(),
}));

function renderRoute(): ReactElement {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return (
    <QueryClientProvider client={client}>
      <LanguageProvider>
        <HomeRoute />
      </LanguageProvider>
    </QueryClientProvider>
  );
}

function setHomeResult(feed: HomeFeed | undefined, pending = false, refetch = jest.fn()): void {
  mockQueryResult = {
    data: feed,
    error: null,
    isPending: pending,
    isError: false,
    isRefetching: false,
    refetch,
  } as unknown as UseQueryResult<HomeFeed>;
}

describe('HomeRoute', () => {
  beforeEach(() => {
    mockPush.mockClear();
    setHomeResult(undefined, true);
  });

  it('renders structured skeletons while the home query is pending', async () => {
    const screen = await render(renderRoute());
    expect(screen.getAllByLabelText(i18n.t('common.loading')).length).toBeGreaterThan(4);
  });

  it('shows category and shelf sections, and routes their taps with API identifiers', async () => {
    setHomeResult(homeFixture.en);
    const screen = await render(renderRoute());
    expect(screen.getByText(homeFixture.en.sections[0]?.title ?? '')).toBeTruthy();
    expect(screen.getByText(homeFixture.en.sections[1]?.title ?? '')).toBeTruthy();
    expect(screen.getAllByLabelText(/product image/i)).toHaveLength(12);

    await fireEvent.press(
      screen.getByRole('button', {
        name: i18n.t('home.category_accessibility', { name: 'Cleanser' }),
      }),
    );
    expect(mockPush).toHaveBeenCalledWith({
      pathname: '/products',
      params: { category: 'cleanser' },
    });

    await fireEvent.press(screen.getAllByRole('button', { name: /Daily Hydration Serum/i })[0]!);
    await waitFor(() => {
      expect(mockPush).toHaveBeenLastCalledWith({
        pathname: '/product/[id]',
        params: { id: expect.any(String) },
      });
    });
  });

  it('renders the empty state when the API returns no sections', async () => {
    setHomeResult({ sections: [] });
    const screen = await render(renderRoute());
    expect(screen.getByText(i18n.t('home.empty_title'))).toBeTruthy();
  });

  it('ignores section types added by a newer backend without crashing the feed', async () => {
    setHomeResult({
      sections: [
        {
          id: 'future_section',
          type: 'future_section_type',
          title: 'Future section',
          items: [],
          next_cursor: null,
        },
      ],
    });
    const screen = await render(renderRoute());
    expect(screen.queryByText('Future section')).toBeNull();
    expect(screen.queryByText(i18n.t('home.empty_title'))).toBeNull();
  });

  it('passes each shelf cursor to the section query when horizontal scrolling reaches the end', async () => {
    const feed = {
      sections: homeFixture.en.sections.map((section) =>
        section.id === 'top_rated' ? { ...section, next_cursor: 'cursor-top-1' } : section,
      ),
    };
    setHomeResult(feed);
    jest.mocked(fetchHomeSection).mockResolvedValueOnce({
      ...homeFixture.en.sections[1]!,
      items: [productCardsFixture[1]!],
      next_cursor: null,
    });
    const screen = await render(renderRoute());
    await fireEvent(screen.getByTestId('home-shelf-top_rated'), 'onEndReached');
    await waitFor(() => {
      expect(fetchHomeSection).toHaveBeenCalledWith('top_rated', 'cursor-top-1');
    });
    expect(await screen.findAllByRole('button', { name: /Gentle Cream Cleanser/i })).toHaveLength(
      2,
    );
  });

  it('uses Retry to refetch failed feeds and supports pull-to-refresh', async () => {
    const refetch = jest.fn();
    mockQueryResult = {
      data: undefined,
      error: new Error('network failed'),
      isPending: false,
      isError: true,
      isRefetching: false,
      refetch,
    } as unknown as UseQueryResult<HomeFeed>;
    const errorScreen = await render(renderRoute());
    await fireEvent.press(errorScreen.getByRole('button', { name: i18n.t('common.retry') }));
    expect(refetch).toHaveBeenCalledTimes(1);

    const refreshRefetch = jest.fn();
    setHomeResult(homeFixture.en, false, refreshRefetch);
    const feedScreen = await render(renderRoute());
    const refreshControl = feedScreen.container.queryAll(
      (instance) => instance.type === 'RCTRefreshControl',
    )[0];
    expect(refreshControl).toBeDefined();
    await refreshHomeFeed(new QueryClient(), refreshRefetch);
    await waitFor(() => {
      expect(refreshRefetch).toHaveBeenCalled();
    });
  });
});
