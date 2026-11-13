import type { ReactElement } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, waitFor } from '@testing-library/react-native';
import { productFixture } from '@/api/fixtures';
import { resetMockProfileStore } from '@/features/profile/profile-api';
import i18n from '@/i18n/i18n';
import { LanguageProvider } from '@/i18n/LanguageProvider';
import { ProductDetailScreen } from './product-detail-screen';

jest.mock('@/config/env', () => ({
  env: { apiUrl: 'https://mock.invalid', useMocks: true },
}));

jest.mock('expo-router', () => ({
  router: { back: jest.fn() },
}));

function renderDetail(productId: string | undefined = productFixture.id): ReactElement {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: false, gcTime: 0 },
    },
  });
  return (
    <QueryClientProvider client={client}>
      <LanguageProvider>
        <ProductDetailScreen productId={productId} />
      </LanguageProvider>
    </QueryClientProvider>
  );
}

describe('ProductDetailScreen & Suitability (US-13, US-17)', () => {
  beforeEach(() => {
    resetMockProfileStore();
  });

  it('renders product detail, suitability card, and toggles product blacklist', async () => {
    const screen = await render(renderDetail());
    await screen.findByText(productFixture.name);

    expect(screen.getByTestId('product-suitability-card')).toBeTruthy();
    expect(screen.getByText(i18n.t('product_detail.verdict_suitable'))).toBeTruthy();

    const blacklistBtn = screen.getByRole('button', {
      name: i18n.t('product_detail.blacklist_add_product'),
    });
    await fireEvent.press(blacklistBtn);

    await waitFor(() => {
      expect(screen.getByText(i18n.t('product_detail.verdict_avoid'))).toBeTruthy();
    });
  });
});
