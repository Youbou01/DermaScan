import type { ReactElement } from 'react';
import { Image, Pressable, StyleSheet, Text, View } from 'react-native';
import { useState } from 'react';
import type { ProductCard as ProductCardData } from '@/api/types';
import { radii, spacing, typography, useThemeColors } from '@/theme/tokens';
import { RiskBadge } from './RiskBadge';
import { ScoreBadge } from './ScoreBadge';

export interface ProductCardProps {
  product: ProductCardData;
  onPress?: (id: string) => void;
}

export function ProductCard({ product, onPress }: ProductCardProps): ReactElement {
  const colors = useThemeColors();
  const [imageFailed, setImageFailed] = useState(false);
  const badge = product.score_band ? (
    product.score_band === 'unknown' ? (
      <RiskBadge level="unknown" />
    ) : (
      <ScoreBadge score={product.score} band={product.score_band} />
    )
  ) : (
    <ScoreBadge score={product.score} />
  );
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={`${product.name}, ${product.brand ?? 'Unknown brand'}`}
      onPress={() => onPress?.(product.id)}
      style={({ pressed }) => [
        styles.card,
        {
          backgroundColor: colors.surface,
          borderColor: colors.border,
          opacity: pressed ? 0.78 : 1,
        },
      ]}
    >
      {product.image_url && !imageFailed ? (
        <Image
          accessibilityLabel={`${product.name} product image`}
          onError={() => setImageFailed(true)}
          source={{ uri: product.image_url }}
          style={[styles.image, { backgroundColor: colors.surfaceMuted }]}
        />
      ) : (
        <View
          accessibilityLabel="Product image unavailable"
          style={[styles.image, styles.placeholder, { backgroundColor: colors.surfaceMuted }]}
        >
          <Text style={[styles.placeholderText, { color: colors.textMuted }]}>◇</Text>
        </View>
      )}
      <View style={styles.details}>
        <Text numberOfLines={2} style={[styles.name, { color: colors.text }]}>
          {product.name}
        </Text>
        <Text numberOfLines={1} style={[styles.brand, { color: colors.textMuted }]}>
          {product.brand ?? 'Brand unavailable'}
        </Text>
        {product.category_slug ? (
          <Text numberOfLines={1} style={[styles.category, { color: colors.textMuted }]}>
            {product.category_slug}
          </Text>
        ) : null}
        {badge}
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  card: {
    minHeight: 116,
    flexDirection: 'row',
    gap: spacing.md,
    padding: spacing.md,
    borderWidth: 1,
    borderRadius: radii.md,
  },
  image: { width: 84, minHeight: 84, borderRadius: radii.sm },
  placeholder: { alignItems: 'center', justifyContent: 'center' },
  placeholderText: { fontSize: 30 },
  details: {
    flex: 1,
    minWidth: 0,
    justifyContent: 'center',
    alignItems: 'flex-start',
    gap: spacing.xs,
  },
  name: {
    fontSize: typography.size.md,
    lineHeight: typography.lineHeight.md,
    fontWeight: typography.weight.semibold,
  },
  brand: { fontSize: typography.size.sm, lineHeight: typography.lineHeight.sm },
  category: {
    fontSize: typography.size.xs,
    lineHeight: typography.lineHeight.xs,
    textTransform: 'capitalize',
  },
});
