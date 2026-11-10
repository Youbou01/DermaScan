import type { ReactElement } from 'react';
import { render } from '@testing-library/react-native';
import { LanguageProvider } from '@/i18n/LanguageProvider';
import { productFixture, profileFixture } from '@/api/fixtures';
import type { ProductDetail } from '@/api/types';
import { ProductDetailScreen } from './product-detail-screen';

let mockAuthenticated = false;
let mockProduct: ProductDetail | undefined;
const mockProfile = { ...profileFixture, blacklisted_product_ids: [productFixture.id] };
jest.mock('expo-router', () => ({ router: { back: jest.fn() } }));
jest.mock('@/features/auth/AuthProvider', () => ({
  useAuth: () => ({
    user: mockAuthenticated ? { id: 'user-1' } : null,
    isAuthenticated: mockAuthenticated,
  }),
}));
jest.mock('@/api/hooks', () => ({
  useProductQuery: () => ({
    data: mockProduct,
    isPending: false,
    isError: false,
    refetch: jest.fn(),
  }),
  useProductSuitabilityQuery: () => ({
    data: {
      product_id: mockProduct?.id,
      suits_profile: false,
      verdict: 'avoid',
      has_risk_alert: true,
      is_blacklisted: true,
      alerts: [
        {
          code: 'blacklisted',
          severity: 'high',
          ingredient_name: null,
          title: 'Blacklisted product',
          detail: 'This product is on your blacklist.',
        },
      ],
    },
    isPending: false,
    isError: false,
  }),
  useProfileQuery: () => ({ data: mockProfile, isPending: false, isError: false }),
  useUpdateProfileMutation: () => ({ mutate: jest.fn(), isPending: false, isError: false }),
}));

function renderDetail(): ReactElement {
  return (
    <LanguageProvider>
      <ProductDetailScreen productId={productFixture.id} />
    </LanguageProvider>
  );
}

describe('personalized product detail', () => {
  beforeEach(() => {
    mockProduct = productFixture;
    mockAuthenticated = false;
  });

  it('shows public product content to a visitor without personalized banners or blacklist actions', async () => {
    const screen = await render(renderDetail());
    expect(screen.getByText(productFixture.name)).toBeTruthy();
    expect(screen.queryByText('Not recommended for your profile')).toBeNull();
    expect(screen.queryByText('Add to blacklist')).toBeNull();
  });

  it('shows suitability and a prominent blacklist warning to a signed-in user', async () => {
    mockAuthenticated = true;
    const screen = await render(renderDetail());
    expect(screen.getByText('Not recommended for your profile')).toBeTruthy();
    expect(screen.getAllByText('This product is on your blacklist.')).toHaveLength(1);
    expect(screen.getByRole('button', { name: 'Remove from blacklist' })).toBeTruthy();
    expect(
      screen.getAllByLabelText('High concern level. Review the ingredient information carefully.'),
    ).toHaveLength(2);
  });
});
