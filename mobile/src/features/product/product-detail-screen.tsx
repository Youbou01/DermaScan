import type { ReactElement } from 'react';
import { useState } from 'react';
import { Image, Pressable, StyleSheet, Text, View } from 'react-native';
import { router } from 'expo-router';
import { ApiError } from '@/api/errors';
import type { ProductIngredient, RiskLevel } from '@/api/types';
import { useProductQuery } from '@/api/hooks';
import { EmptyState, ErrorState, RiskBadge, ScoreBadge, Screen, Skeleton } from '@/components';
import {
  useBlacklistQuery,
  useProductSuitabilityQuery,
  useToggleBlacklistIngredientMutation,
  useToggleBlacklistProductMutation,
} from '@/features/profile/profile-api';
import { useTranslation } from '@/i18n/useTranslation';
import { radii, spacing, typography, useThemeColors } from '@/theme/tokens';
import { IngredientRationaleModal } from './components/IngredientRationaleModal';
import { formatScoreCoverage, productDetailCopy } from './product-detail.copy';

const productNotFoundType = 'urn:skincare:problem:product-not-found';

export interface ProductDetailScreenProps {
  productId: string | undefined;
}

export function ProductDetailScreen({ productId }: ProductDetailScreenProps): ReactElement {
  const colors = useThemeColors();
  const { t } = useTranslation();
  const productQuery = useProductQuery(productId);
  const [selectedIngredient, setSelectedIngredient] = useState<ProductIngredient | null>(null);
  const [failedImageUrl, setFailedImageUrl] = useState<string | null>(null);

  const suitabilityQuery = useProductSuitabilityQuery(
    productId,
    productQuery.data?.ingredients ?? [],
  );
  const blacklistQuery = useBlacklistQuery();
  const toggleBlacklistProduct = useToggleBlacklistProductMutation();
  const toggleBlacklistIngredient = useToggleBlacklistIngredientMutation();

  if (!productId) {
    return (
      <Screen>
        <ErrorState
          title={productDetailCopy.missingIdTitle}
          description={productDetailCopy.missingIdDescription}
        />
      </Screen>
    );
  }

  if (productQuery.isPending) {
    return (
      <Screen contentContainerStyle={styles.loadingContent}>
        <Skeleton height={220} />
        <Skeleton variant="text" width="72%" />
        <Skeleton variant="text" width="46%" />
        <Skeleton height={80} />
        <Skeleton height={80} />
      </Screen>
    );
  }

  if (productQuery.isError && productQuery.data === undefined) {
    const isNotFound =
      productQuery.error instanceof ApiError && productQuery.error.type === productNotFoundType;
    return (
      <Screen>
        <ErrorState
          title={isNotFound ? productDetailCopy.notFoundTitle : productDetailCopy.genericErrorTitle}
          description={
            isNotFound
              ? productDetailCopy.notFoundDescription
              : productDetailCopy.genericErrorDescription
          }
          buttonLabel={productDetailCopy.retryLabel}
          onRetry={() => {
            void productQuery.refetch();
          }}
        />
      </Screen>
    );
  }

  const product = productQuery.data;
  if (!product) {
    return (
      <Screen>
        <EmptyState
          title={productDetailCopy.notFoundTitle}
          description={productDetailCopy.notFoundDescription}
        />
      </Screen>
    );
  }

  const imageAvailable = product.image_url !== null && failedImageUrl !== product.image_url;
  const suitability = suitabilityQuery.data;
  const isProductBlacklisted = Boolean(
    blacklistQuery.data?.product_ids.includes(product.id) || suitability?.is_blacklisted,
  );
  const selectedIngBlacklisted = Boolean(
    selectedIngredient?.ingredient_id &&
    blacklistQuery.data?.ingredient_ids.includes(selectedIngredient.ingredient_id),
  );

  const verdictColor =
    suitability?.verdict === 'avoid'
      ? colors.high
      : suitability?.verdict === 'caution'
        ? colors.moderate
        : colors.low;
  const verdictSurface =
    suitability?.verdict === 'avoid'
      ? colors.highSurface
      : suitability?.verdict === 'caution'
        ? colors.moderateSurface
        : colors.lowSurface;
  const verdictIcon =
    suitability?.verdict === 'avoid' ? '⬟' : suitability?.verdict === 'caution' ? '△' : '○';
  const verdictLabel =
    suitability?.verdict === 'avoid'
      ? t('product_detail.verdict_avoid')
      : suitability?.verdict === 'caution'
        ? t('product_detail.verdict_caution')
        : t('product_detail.verdict_suitable');

  return (
    <Screen contentContainerStyle={styles.content}>
      <Pressable
        accessibilityRole="button"
        accessibilityLabel={productDetailCopy.backAccessibilityLabel}
        onPress={() => router.back()}
        style={({ pressed }) => [
          styles.backButton,
          { borderColor: colors.border, opacity: pressed ? 0.7 : 1 },
        ]}
      >
        <Text style={[styles.backLabel, { color: colors.primary }]}>
          {productDetailCopy.backLabel}
        </Text>
      </Pressable>

      <View style={styles.productHeader}>
        {imageAvailable ? (
          <Image
            accessibilityLabel={`${product.name} product image`}
            onError={() => setFailedImageUrl(product.image_url)}
            resizeMode="contain"
            source={{ uri: product.image_url ?? undefined }}
            style={[styles.productImage, { backgroundColor: colors.surfaceMuted }]}
          />
        ) : (
          <View
            accessibilityLabel={productDetailCopy.imageUnavailable}
            style={[
              styles.productImage,
              styles.imagePlaceholder,
              { backgroundColor: colors.surfaceMuted },
            ]}
          >
            <Text
              accessibilityElementsHidden
              style={[styles.imagePlaceholderText, { color: colors.textMuted }]}
            >
              ◇
            </Text>
          </View>
        )}
        <Text accessibilityRole="header" style={[styles.productName, { color: colors.text }]}>
          {product.name}
        </Text>
        <Text style={[styles.productMeta, { color: colors.textMuted }]}>
          {product.brand ?? productDetailCopy.brandUnavailable}
        </Text>
        <Text style={[styles.productMeta, { color: colors.textMuted }]}>
          {product.category?.name ?? productDetailCopy.categoryUnavailable}
        </Text>
        <Pressable
          accessibilityRole="button"
          accessibilityLabel={
            isProductBlacklisted
              ? t('product_detail.blacklist_remove_product')
              : t('product_detail.blacklist_add_product')
          }
          onPress={() => {
            void toggleBlacklistProduct.mutateAsync(product.id);
          }}
          style={[
            styles.blacklistButton,
            {
              borderColor: isProductBlacklisted ? colors.high : colors.border,
              backgroundColor: isProductBlacklisted ? colors.highSurface : colors.surface,
            },
          ]}
        >
          <Text
            style={[
              styles.blacklistButtonText,
              { color: isProductBlacklisted ? colors.high : colors.text },
            ]}
          >
            {isProductBlacklisted
              ? t('product_detail.blacklist_remove_product')
              : t('product_detail.blacklist_add_product')}
          </Text>
        </Pressable>
      </View>

      <View
        style={[
          styles.scoreSection,
          { backgroundColor: colors.surface, borderColor: colors.border },
        ]}
      >
        <Text accessibilityRole="header" style={[styles.sectionHeading, { color: colors.text }]}>
          {productDetailCopy.riskIndicatorHeading}
        </Text>
        <ScoreBadge
          score={product.score}
          band={product.score === null ? 'unknown' : product.score_band}
        />
        {product.score_is_estimated ? (
          <Text style={[styles.coverage, { color: colors.textMuted }]}>
            {t('product_detail.estimated_note')}
          </Text>
        ) : null}
        <Text style={[styles.coverage, { color: colors.textMuted }]}>
          {formatScoreCoverage(product.score_coverage)}
        </Text>
        {product.summary ? (
          <View style={styles.summaryBox}>
            <Text style={[styles.summaryTitle, { color: colors.text }]}>
              {t('product_detail.summary_heading')}
            </Text>
            <Text style={[styles.summaryBody, { color: colors.textMuted }]}>{product.summary}</Text>
          </View>
        ) : null}
      </View>

      {suitability ? (
        <View
          testID="product-suitability-card"
          style={[
            styles.suitabilitySection,
            { backgroundColor: verdictSurface, borderColor: verdictColor },
          ]}
        >
          <Text accessibilityRole="header" style={[styles.sectionHeading, { color: verdictColor }]}>
            {verdictIcon} {t('product_detail.suitability_heading')}
          </Text>
          <Text style={[styles.verdictText, { color: verdictColor }]}>{verdictLabel}</Text>
          {suitability.alerts.map((alert, idx) => (
            <View
              key={`${alert.code}-${alert.ingredient_name}-${idx}`}
              style={[
                styles.alertCard,
                { backgroundColor: colors.surface, borderColor: verdictColor },
              ]}
            >
              <Text style={[styles.alertTitle, { color: colors.text }]}>
                {alert.severity === 'high' ? '⬟ ' : '△ '}
                {alert.title} ({alert.ingredient_name})
              </Text>
              <Text style={[styles.alertDetail, { color: colors.textMuted }]}>{alert.detail}</Text>
            </View>
          ))}
        </View>
      ) : null}

      <View style={styles.ingredientsSection}>
        <Text accessibilityRole="header" style={[styles.sectionHeading, { color: colors.text }]}>
          {productDetailCopy.ingredientsHeading}
        </Text>
        {product.ingredients.length > 0 ? (
          <View style={styles.ingredientList}>
            {product.ingredients.map((ingredient) => (
              <IngredientRow
                ingredient={ingredient}
                key={`${ingredient.position}-${ingredient.name}`}
                onPress={() => setSelectedIngredient(ingredient)}
              />
            ))}
          </View>
        ) : (
          <EmptyState
            title={productDetailCopy.ingredientsEmptyTitle}
            description={productDetailCopy.ingredientsEmptyDescription}
          />
        )}
      </View>

      <Text style={[styles.disclaimer, { color: colors.textMuted }]}>
        {productDetailCopy.disclaimer}
      </Text>

      <IngredientRationaleModal
        ingredient={selectedIngredient}
        isBlacklisted={selectedIngBlacklisted}
        onClose={() => setSelectedIngredient(null)}
        onToggleBlacklistIngredient={(ingId) => {
          void toggleBlacklistIngredient.mutateAsync(ingId);
        }}
      />
    </Screen>
  );
}

interface IngredientRowProps {
  ingredient: ProductIngredient;
  onPress: () => void;
}

function IngredientRow({ ingredient, onPress }: IngredientRowProps): ReactElement {
  const colors = useThemeColors();
  const level: RiskLevel = ingredient.matched ? ingredient.risk_level : 'unknown';

  return (
    <Pressable
      accessibilityHint={productDetailCopy.openRationaleHint}
      accessibilityLabel={`${ingredient.position}. ${ingredient.name}`}
      accessibilityRole="button"
      onPress={onPress}
      style={({ pressed }) => [
        styles.ingredientRow,
        {
          backgroundColor: colors.surface,
          borderColor: colors.border,
          opacity: pressed ? 0.75 : 1,
        },
      ]}
    >
      <View style={styles.ingredientText}>
        <Text style={[styles.ingredientName, { color: colors.text }]}>
          {ingredient.position}. {ingredient.name}
        </Text>
        {ingredient.inci_name && ingredient.inci_name !== ingredient.name ? (
          <Text style={[styles.inciName, { color: colors.textMuted }]}>{ingredient.inci_name}</Text>
        ) : null}
      </View>
      <RiskBadge level={level} />
    </Pressable>
  );
}

const styles = StyleSheet.create({
  content: { gap: spacing.xl, padding: spacing.lg, paddingBottom: spacing.xxxl },
  loadingContent: { gap: spacing.lg, padding: spacing.lg },
  backButton: {
    minHeight: 44,
    alignSelf: 'flex-start',
    justifyContent: 'center',
    paddingHorizontal: spacing.md,
    borderWidth: 1,
    borderRadius: radii.md,
  },
  backLabel: { fontSize: typography.size.md, lineHeight: typography.lineHeight.md },
  productHeader: { alignItems: 'center', gap: spacing.sm, paddingVertical: spacing.md },
  productImage: { width: 180, height: 180, borderRadius: radii.md },
  imagePlaceholder: { alignItems: 'center', justifyContent: 'center' },
  imagePlaceholderText: { fontSize: typography.size.display },
  productName: {
    textAlign: 'center',
    fontSize: typography.size.xl,
    lineHeight: typography.lineHeight.xl,
    fontWeight: typography.weight.bold,
  },
  productMeta: {
    textAlign: 'center',
    fontSize: typography.size.md,
    lineHeight: typography.lineHeight.md,
  },
  blacklistButton: {
    minHeight: 44,
    justifyContent: 'center',
    paddingHorizontal: spacing.md,
    borderWidth: 1,
    borderRadius: radii.md,
    marginTop: spacing.xs,
  },
  blacklistButtonText: {
    fontSize: typography.size.xs,
    fontWeight: typography.weight.semibold,
  },
  scoreSection: {
    alignItems: 'flex-start',
    gap: spacing.md,
    padding: spacing.lg,
    borderWidth: 1,
    borderRadius: radii.md,
  },
  sectionHeading: {
    fontSize: typography.size.lg,
    lineHeight: typography.lineHeight.lg,
    fontWeight: typography.weight.bold,
  },
  coverage: { fontSize: typography.size.sm, lineHeight: typography.lineHeight.sm },
  summaryBox: {
    gap: spacing.xs,
    marginTop: spacing.xs,
  },
  summaryTitle: {
    fontSize: typography.size.sm,
    fontWeight: typography.weight.semibold,
  },
  summaryBody: {
    fontSize: typography.size.sm,
    lineHeight: typography.lineHeight.sm,
  },
  suitabilitySection: {
    gap: spacing.sm,
    padding: spacing.lg,
    borderWidth: 1,
    borderRadius: radii.md,
  },
  verdictText: {
    fontSize: typography.size.md,
    fontWeight: typography.weight.semibold,
  },
  alertCard: {
    gap: spacing.xs,
    padding: spacing.md,
    borderWidth: 1,
    borderRadius: radii.sm,
  },
  alertTitle: {
    fontSize: typography.size.sm,
    fontWeight: typography.weight.bold,
  },
  alertDetail: {
    fontSize: typography.size.xs,
    lineHeight: typography.lineHeight.xs,
  },
  ingredientsSection: { gap: spacing.md },
  ingredientList: { gap: spacing.sm },
  ingredientRow: {
    minHeight: 56,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: spacing.md,
    padding: spacing.md,
    borderWidth: 1,
    borderRadius: radii.md,
  },
  ingredientText: { flex: 1, minWidth: 0, gap: spacing.xs },
  ingredientName: {
    fontSize: typography.size.md,
    lineHeight: typography.lineHeight.md,
    fontWeight: typography.weight.medium,
  },
  inciName: { fontSize: typography.size.sm, lineHeight: typography.lineHeight.sm },
  disclaimer: { fontSize: typography.size.sm, lineHeight: typography.lineHeight.sm },
});
