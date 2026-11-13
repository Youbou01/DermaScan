import type { ReactElement } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, waitFor } from '@testing-library/react-native';
import i18n from '@/i18n/i18n';
import { LanguageProvider } from '@/i18n/LanguageProvider';
import { ProductCatalogScreen } from './ProductCatalogScreen';

const mockPush = jest.fn();

jest.mock('@/config/env', () => ({
  env: { apiUrl: 'https://mock.invalid', useMocks: true },
}));

jest.mock('expo-router', () => ({
  useRouter: () => ({ push: mockPush }),
}));

function renderCatalog(initialCategory?: string): ReactElement {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: false, gcTime: 0 },
    },
  });
  return (
    <QueryClientProvider client={client}>
      <LanguageProvider>
        <ProductCatalogScreen initialCategory={initialCategory} />
      </LanguageProvider>
    </QueryClientProvider>
  );
}

describe('ProductCatalogScreen (US-05, US-06)', () => {
  beforeEach(() => {
    mockPush.mockClear();
  });

  it('filters products by search query and resets filters', async () => {
    const screen = await render(renderCatalog());
    await screen.findByText(i18n.t('search.title'));
    await screen.findByText('Daily Hydration Serum');

    const input = screen.getByLabelText(i18n.t('search.query_label'));
    await fireEvent.changeText(input, 'Sunscreen');

    await waitFor(() => {
      expect(screen.getByText('Daily Mineral Sunscreen SPF 50')).toBeTruthy();
      expect(screen.queryByText('Daily Hydration Serum')).toBeNull();
    });

    await fireEvent.press(screen.getByRole('button', { name: i18n.t('search.clear_filters') }));

    await waitFor(() => {
      expect(screen.getByText('Daily Hydration Serum')).toBeTruthy();
    });
  });

  it('pre-filters by initialCategory when navigated from HomeScreen', async () => {
    const screen = await render(renderCatalog('cleanser'));
    await screen.findByText('Gentle Cream Cleanser');

    expect(screen.queryByText('Cloud Cream Moisturizer')).toBeNull();
  });

  it('combines text search query with category filter', async () => {
    const screen = await render(renderCatalog('serum'));
    await screen.findByText('Daily Hydration Serum');

    const input = screen.getByLabelText(i18n.t('search.query_label'));
    await fireEvent.changeText(input, 'Hydration');

    await waitFor(() => {
      expect(screen.getByText('Daily Hydration Serum')).toBeTruthy();
    });
  });
});
