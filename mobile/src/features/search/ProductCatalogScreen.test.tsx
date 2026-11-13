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

  it('adds multiple included and excluded ingredient chips via the add buttons and removes them', async () => {
    const screen = await render(renderCatalog());
    await screen.findByText(i18n.t('search.title'));

    const includeInput = screen.getByLabelText(i18n.t('search.include_label'));
    const addIncludeBtn = screen.getByRole('button', {
      name: i18n.t('search.add_include_button'),
    });

    await fireEvent.changeText(includeInput, 'Niacinamide');
    await fireEvent.press(addIncludeBtn);

    await fireEvent.changeText(includeInput, 'Glycerin');
    await fireEvent.press(addIncludeBtn);

    expect(
      screen.getByRole('button', {
        name: i18n.t('search.remove_include_chip', { name: 'Niacinamide' }),
      }),
    ).toBeTruthy();
    expect(
      screen.getByRole('button', {
        name: i18n.t('search.remove_include_chip', { name: 'Glycerin' }),
      }),
    ).toBeTruthy();

    const excludeInput = screen.getByLabelText(i18n.t('search.exclude_label'));
    const addExcludeBtn = screen.getByRole('button', {
      name: i18n.t('search.add_exclude_button'),
    });

    await fireEvent.changeText(excludeInput, 'Parfum');
    await fireEvent.press(addExcludeBtn);

    const parfumChip = screen.getByRole('button', {
      name: i18n.t('search.remove_exclude_chip', { name: 'Parfum' }),
    });
    expect(parfumChip).toBeTruthy();

    await fireEvent.press(parfumChip);
    expect(
      screen.queryByRole('button', {
        name: i18n.t('search.remove_exclude_chip', { name: 'Parfum' }),
      }),
    ).toBeNull();
  });

  it('pre-filters by initialCategory when navigated from HomeScreen', async () => {
    const screen = await render(renderCatalog('cleanser'));
    await screen.findByText('Gentle Cream Cleanser');

    expect(screen.queryByText('Cloud Cream Moisturizer')).toBeNull();
  });
});
