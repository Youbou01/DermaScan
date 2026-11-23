import { render, screen, fireEvent } from '@testing-library/react-native';
import { Linking } from 'react-native';

import { useOffers, useUserId } from '@/lib/api/queries';
import type { Offer, OfferList } from '@/lib/api/types';

import { WhereToBuy } from '../WhereToBuy';

jest.mock('@/lib/api/queries', () => ({
  useOffers: jest.fn(),
  useUserId: jest.fn(),
}));

jest.mock('heroui-native', () => {
  const React = require('react');
  const { Pressable, Text, View } = require('react-native');
  const Button = ({ children, onPress, accessibilityLabel }: any) =>
    React.createElement(Pressable, { onPress, accessibilityLabel }, children);
  Button.Label = ({ children }: any) => React.createElement(Text, null, children);
  const Typography = ({ children, style }: any) => React.createElement(Text, { style }, children);
  return { Button, Skeleton: () => React.createElement(View), Typography };
});

const mockedUseOffers = jest.mocked(useOffers);
const mockedUseUserId = jest.mocked(useUserId);

function makeOffer(overrides: Partial<Offer> & { name: string }): Offer {
  const { name, ...rest } = overrides;
  return {
    id: `offer-${name}`,
    retailer: {
      name,
      domain: `${name.toLowerCase().replace(' ', '')}.example.com`,
      logo_url: null,
      is_affiliate: false,
      affiliate_label: null,
    },
    price: '15.50',
    currency: 'EUR',
    url: `https://${name.toLowerCase().replace(' ', '')}.example.com/p`,
    stock_state: 'in_stock',
    freshness: 'fresh',
    last_checked_at: '2026-11-23T10:00:00Z',
    is_cheapest: false,
    ...rest,
  };
}

function mockOffers(list: OfferList | undefined, extra: Record<string, unknown> = {}) {
  mockedUseOffers.mockReturnValue({
    data: list,
    isLoading: false,
    error: null,
    refetch: jest.fn(),
    ...extra,
  } as unknown as ReturnType<typeof useOffers>);
}

const shopA = makeOffer({ name: 'Shop A', price: '15.50' });
const shopB = makeOffer({ name: 'Shop B', price: '12.00', is_cheapest: true });

beforeEach(() => {
  jest.clearAllMocks();
  mockedUseUserId.mockReturnValue('user-1');
});

describe('WhereToBuy', () => {
  it('asks to sign in when signed out', async () => {
    mockedUseUserId.mockReturnValue(undefined);
    mockOffers(undefined);
    await render(<WhereToBuy productId="p1" />);
    expect(screen.getByText('Sign in to see where to buy this product.')).toBeTruthy();
  });

  it('shows the loading state', async () => {
    mockOffers(undefined, { isLoading: true });
    await render(<WhereToBuy productId="p1" />);
    expect(screen.getByLabelText('Loading')).toBeTruthy();
  });

  it('shows an error message', async () => {
    mockOffers(undefined, { error: new Error('boom') });
    await render(<WhereToBuy productId="p1" />);
    expect(screen.getByText('Could not load where to buy.')).toBeTruthy();
  });

  it('shows the empty state when there are no offers', async () => {
    mockOffers({ product_id: 'p1', cheapest_offer_id: null, mixed_currencies: false, offers: [] });
    await render(<WhereToBuy productId="p1" />);
    expect(screen.getByText('Not sold online')).toBeTruthy();
  });

  it('lists offers and marks only the cheapest', async () => {
    mockOffers({
      product_id: 'p1',
      cheapest_offer_id: shopB.id,
      mixed_currencies: false,
      offers: [shopA, shopB],
    });
    await render(<WhereToBuy productId="p1" />);
    expect(screen.getByText('Where to buy')).toBeTruthy();
    expect(screen.getByText('Shop A')).toBeTruthy();
    expect(screen.getByText('Shop B')).toBeTruthy();
    expect(screen.getAllByText('Cheapest')).toHaveLength(1);
    expect(screen.getByText(/12[.,]00/)).toBeTruthy();
  });

  it('labels stale offers', async () => {
    const stale = makeOffer({ name: 'Shop Old', freshness: 'stale' });
    mockOffers({
      product_id: 'p1',
      cheapest_offer_id: null,
      mixed_currencies: false,
      offers: [stale],
    });
    await render(<WhereToBuy productId="p1" />);
    expect(screen.getByText('Price may be outdated')).toBeTruthy();
    expect(screen.queryByText('Cheapest')).toBeNull();
  });

  it('hides the cheapest badge when currencies are mixed', async () => {
    const usd = makeOffer({ name: 'Shop US', price: '10.00', currency: 'USD', is_cheapest: true });
    mockOffers({
      product_id: 'p1',
      cheapest_offer_id: null,
      mixed_currencies: true,
      offers: [shopA, usd],
    });
    await render(<WhereToBuy productId="p1" />);
    expect(
      screen.getByText('Prices are in different currencies, so no cheapest offer is shown.'),
    ).toBeTruthy();
    expect(screen.queryByText('Cheapest')).toBeNull();
  });

  it('opens the offer url', async () => {
    const spy = jest.spyOn(Linking, 'openURL').mockResolvedValue();
    mockOffers({
      product_id: 'p1',
      cheapest_offer_id: shopB.id,
      mixed_currencies: false,
      offers: [shopB],
    });
    await render(<WhereToBuy productId="p1" />);
    await fireEvent.press(screen.getByLabelText('Go to Shop B'));
    expect(spy).toHaveBeenCalledWith(shopB.url);
  });
});
