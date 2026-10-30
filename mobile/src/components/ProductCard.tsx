import type { ReactElement } from 'react';
import { Image, Pressable, StyleSheet, Text, View, type ImageSourcePropType } from 'react-native';
import { useState } from 'react';
import type { ProductCard as ProductCardData } from '@/api/types';
import { radii, spacing, typography, useThemeColors } from '@/theme/tokens';
import { RiskBadge } from './RiskBadge';
import { ScoreBadge } from './ScoreBadge';
import { getLocalizedCategorySlug } from '@/i18n/category';
import { useTranslation } from '@/i18n/useTranslation';

export interface ProductCardProps {
  product: ProductCardData;
  onPress?: (id: string) => void;
  layout?: 'row' | 'shelf';
  artwork?: ImageSourcePropType;
}

export function ProductCard({
  product,
  onPress,
  layout = 'row',
  artwork,
}: ProductCardProps): ReactElement {
  const colors = useThemeColors();
  const { t } = useTranslation();
  const categoryLabel = product.category_slug
    ? getLocalizedCategorySlug(product.category_slug)
    : null;
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
      accessibilityLabel={`${product.name}, ${product.brand ?? t('errors.unknown_brand')}`}
      onPress={() => onPress?.(product.id)}
      style={({ pressed }) => [
        styles.card,
        layout === 'shelf' && styles.shelfCard,
        {
          backgroundColor: colors.surface,
          borderColor: colors.border,
          opacity: pressed ? 0.78 : 1,
        },
      ]}
    >
      {product.image_url && !imageFailed ? (
        <Image
          accessibilityLabel={t('errors.product_image', { name: product.name })}
          onError={() => setImageFailed(true)}
          resizeMode="cover"
          source={{ uri: product.image_url }}
          style={[
            styles.image,
            layout === 'shelf' && styles.shelfImage,
            { backgroundColor: colors.surfaceMuted },
          ]}
        />
      ) : artwork ? (
        <Image
          accessibilityLabel={t('errors.product_image', { name: product.name })}
          resizeMode="cover"
          source={artwork}
          style={[
            styles.image,
            layout === 'shelf' && styles.shelfImage,
            { backgroundColor: colors.surfaceMuted },
          ]}
        />
      ) : (
        <View
          accessibilityLabel={t('errors.product_unavailable')}
          style={[
            styles.image,
            layout === 'shelf' && styles.shelfImage,
            styles.placeholder,
            { backgroundColor: colors.surfaceMuted },
          ]}
        >
          <Text style={[styles.placeholderText, { color: colors.textMuted }]}>DS</Text>
        </View>
      )}
      <View style={[styles.details, layout === 'shelf' && styles.shelfDetails]}>
        <Text numberOfLines={2} style={[styles.name, { color: colors.text }]}>
          {product.name}
        </Text>
        <Text numberOfLines={1} style={[styles.brand, { color: colors.textMuted }]}>
          {product.brand ?? t('errors.brand_unavailable')}
        </Text>
        {categoryLabel ? (
          <Text numberOfLines={1} style={[styles.category, { color: colors.textMuted }]}>
            {categoryLabel}
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
  shelfCard: { minHeight: 0, flexDirection: 'column', gap: 0, padding: 0, overflow: 'hidden' },
  shelfImage: { width: '100%', height: 176, minHeight: 176, borderRadius: 0 },
  placeholder: { alignItems: 'center', justifyContent: 'center' },
  placeholderText: { fontSize: 30, fontWeight: '700', letterSpacing: 2 },
  details: {
    flex: 1,
    minWidth: 0,
    justifyContent: 'center',
    alignItems: 'flex-start',
    gap: spacing.xs,
  },
  shelfDetails: { paddingHorizontal: spacing.md, paddingVertical: spacing.md },
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
