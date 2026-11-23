import type { ReactNode } from 'react';
import { Image, Linking, View } from 'react-native';
import { Button } from 'heroui-native';
import { AppText } from './AppText';
import { DataState, LoadingState, SignInGate } from './DataState';
import { useOffers, useUserId } from '@/lib/api/queries';
import type { Offer } from '@/lib/api/types';
import { colors } from '@/lib/theme';

const STOCK = {
  in_stock: { label: 'In stock', color: colors.green, background: colors.greenSoft },
  out_of_stock: { label: 'Out of stock', color: colors.red, background: colors.redSoft },
  unknown: { label: 'Availability unknown', color: colors.muted, background: colors.border },
} as const;

function formatPrice(price: string, currency: string, locale: string): string {
  const value = Number(price);
  if (!Number.isFinite(value)) return `${price} ${currency}`;
  try {
    return new Intl.NumberFormat(locale, { style: 'currency', currency }).format(value);
  } catch {
    return `${price} ${currency}`;
  }
}

function initials(name: string): string {
  const letters = name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((word) => word.charAt(0).toUpperCase())
    .join('');
  return letters || '?';
}

function openStore(url: string) {
  Linking.openURL(url).catch(() => undefined);
}

function Badge({ label, color, background }: { label: string; color: string; background: string }) {
  return (
    <View
      style={{
        backgroundColor: background,
        borderRadius: 999,
        paddingHorizontal: 10,
        paddingVertical: 4,
      }}
    >
      <AppText weight="semibold" style={{ color, fontSize: 12 }}>
        {label}
      </AppText>
    </View>
  );
}

function OfferCard({
  offer,
  showCheapest,
  locale,
}: {
  offer: Offer;
  showCheapest: boolean;
  locale: string;
}) {
  const { retailer } = offer;
  const cheapest = showCheapest && offer.is_cheapest;
  const stock = STOCK[offer.stock_state];
  return (
    <View
      style={{
        backgroundColor: colors.white,
        borderRadius: 16,
        borderWidth: cheapest ? 2 : 1,
        borderColor: cheapest ? colors.green : colors.border,
        padding: 14,
        gap: 12,
      }}
    >
      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 12 }}>
        <View
          style={{
            width: 40,
            height: 40,
            borderRadius: 20,
            backgroundColor: colors.peach,
            alignItems: 'center',
            justifyContent: 'center',
            overflow: 'hidden',
          }}
        >
          {retailer.logo_url ? (
            <Image
              source={{ uri: retailer.logo_url }}
              style={{ width: 40, height: 40 }}
              resizeMode="contain"
              accessibilityIgnoresInvertColors
            />
          ) : (
            <AppText weight="bold">{initials(retailer.name)}</AppText>
          )}
        </View>
        <View style={{ flex: 1, gap: 2 }}>
          <AppText weight="semibold">{retailer.name}</AppText>
          {retailer.is_affiliate ? (
            <AppText style={{ color: colors.muted, fontSize: 12 }}>
              {retailer.affiliate_label ?? 'Affiliate link'}
            </AppText>
          ) : null}
        </View>
        <AppText weight="bold" style={{ fontSize: 16 }}>
          {formatPrice(offer.price, offer.currency, locale)}
        </AppText>
      </View>
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8 }}>
        {cheapest ? (
          <Badge label={'Cheapest'} color={colors.green} background={colors.greenSoft} />
        ) : null}
        <Badge label={stock.label} color={stock.color} background={stock.background} />
        {offer.freshness === 'stale' ? (
          <Badge
            label={'Price may be outdated'}
            color={colors.orange}
            background={colors.orangeSoft}
          />
        ) : null}
      </View>
      <Button
        variant="secondary"
        accessibilityLabel={`Go to ${retailer.name}`}
        onPress={() => openStore(offer.url)}
      >
        <Button.Label>{'Go to store'}</Button.Label>
      </Button>
    </View>
  );
}

export function WhereToBuy({ productId }: { productId: string }) {
  const uid = useUserId();
  const { data, isLoading, error, refetch } = useOffers(productId);
  const retry = () => {
    void refetch();
  };

  let body: ReactNode;
  if (!uid) {
    body = <SignInGate message={'Sign in to see where to buy this product.'} />;
  } else if (isLoading) {
    body = <LoadingState />;
  } else if (error) {
    body = (
      <DataState
        error={error}
        message={'Could not load where to buy.'}
        action={'Try again'}
        onAction={retry}
      />
    );
  } else if (!data || data.offers.length === 0) {
    body = <DataState message={'Not sold online'} action={'Try again'} onAction={retry} />;
  } else {
    body = (
      <View style={{ gap: 12 }}>
        {data.mixed_currencies ? (
          <AppText style={{ color: colors.muted, fontSize: 13 }}>
            {'Prices are in different currencies, so no cheapest offer is shown.'}
          </AppText>
        ) : null}
        {data.offers.map((offer) => (
          <OfferCard
            key={offer.id}
            offer={offer}
            showCheapest={!data.mixed_currencies}
            locale="en"
          />
        ))}
      </View>
    );
  }

  return (
    <View style={{ gap: 12 }}>
      <AppText weight="bold" style={{ fontSize: 18 }}>
        {'Where to buy'}
      </AppText>
      {body}
    </View>
  );
}
