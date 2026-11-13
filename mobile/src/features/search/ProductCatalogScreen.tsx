import { useRouter, type Href } from 'expo-router';
import { useState, type ReactElement } from 'react';
import { Pressable, StyleSheet, Text, TextInput, View } from 'react-native';
import type { RiskLevel } from '@/api/types';
import { EmptyState, ErrorState, ProductCard, Screen, Skeleton } from '@/components';
import { getProductArtwork } from '@/features/home/product-artwork';
import { getLocalizedCategorySlug } from '@/i18n/category';
import { useTranslation } from '@/i18n/useTranslation';
import { radii, spacing, typography, useThemeColors } from '@/theme/tokens';
import { useCatalogProductsQuery } from './search-api';

const FILTER_CATEGORIES = [
  'cleanser',
  'toner',
  'serum',
  'moisturizer',
  'sunscreen',
  'eye-care',
  'body-lotion',
  'lip-care',
] as const;

const FILTER_BANDS: readonly RiskLevel[] = ['low', 'moderate', 'high'];
const MIN_SCORES: readonly (number | null)[] = [null, 50, 75];

export interface ProductCatalogScreenProps {
  readonly initialCategory?: string;
}

export function ProductCatalogScreen({ initialCategory }: ProductCatalogScreenProps): ReactElement {
  const router = useRouter();
  const colors = useThemeColors();
  const { t } = useTranslation();

  const [query, setQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string | null>(initialCategory ?? null);
  const [selectedBand, setSelectedBand] = useState<RiskLevel | null>(null);
  const [minScore, setMinScore] = useState<number | null>(null);
  const [includeIngredient, setIncludeIngredient] = useState('');
  const [excludeIngredient, setExcludeIngredient] = useState('');

  const catalogQuery = useCatalogProductsQuery({
    query,
    category: selectedCategory,
    band: selectedBand,
    minScore,
    includeIngredient,
    excludeIngredient,
  });

  const handleResetFilters = (): void => {
    setQuery('');
    setSelectedCategory(null);
    setSelectedBand(null);
    setMinScore(null);
    setIncludeIngredient('');
    setExcludeIngredient('');
  };

  const products = catalogQuery.data ?? [];

  return (
    <Screen contentContainerStyle={styles.content}>
      <Pressable
        accessibilityRole="button"
        accessibilityLabel={t('auth.back_home')}
        onPress={() => router.push('/' as unknown as Href)}
        style={[styles.backButton, { borderColor: colors.border }]}
      >
        <Text style={[styles.backText, { color: colors.primary }]}>‹ {t('auth.back_home')}</Text>
      </Pressable>

      <Text accessibilityRole="header" style={[styles.title, { color: colors.text }]}>
        {t('search.title')}
      </Text>

      <View style={styles.searchGroup}>
        <Text style={[styles.label, { color: colors.text }]}>{t('search.query_label')}</Text>
        <TextInput
          accessibilityLabel={t('search.query_label')}
          autoCapitalize="none"
          autoCorrect={false}
          onChangeText={setQuery}
          placeholder={t('search.query_placeholder')}
          placeholderTextColor={colors.textMuted}
          returnKeyType="search"
          style={[
            styles.input,
            {
              color: colors.text,
              backgroundColor: colors.surface,
              borderColor: colors.border,
            },
          ]}
          value={query}
        />
      </View>

      <Text style={[styles.label, { color: colors.text }]}>{t('search.category_heading')}</Text>
      <View style={styles.pillsRow}>
        <Pressable
          accessibilityRole="button"
          accessibilityLabel={t('search.all_categories')}
          accessibilityState={{ selected: selectedCategory === null }}
          onPress={() => setSelectedCategory(null)}
          style={[
            styles.pill,
            {
              backgroundColor: selectedCategory === null ? colors.primary : colors.surface,
              borderColor: selectedCategory === null ? colors.primary : colors.border,
            },
          ]}
        >
          <Text
            style={[
              styles.pillText,
              { color: selectedCategory === null ? colors.onPrimary : colors.text },
            ]}
          >
            {t('search.all_categories')}
          </Text>
        </Pressable>
        {FILTER_CATEGORIES.map((slug) => {
          const selected = selectedCategory === slug;
          const label = getLocalizedCategorySlug(slug) ?? slug;
          return (
            <Pressable
              key={slug}
              accessibilityRole="button"
              accessibilityLabel={label}
              accessibilityState={{ selected }}
              onPress={() => setSelectedCategory(selected ? null : slug)}
              style={[
                styles.pill,
                {
                  backgroundColor: selected ? colors.primary : colors.surface,
                  borderColor: selected ? colors.primary : colors.border,
                },
              ]}
            >
              <Text style={[styles.pillText, { color: selected ? colors.onPrimary : colors.text }]}>
                {label}
              </Text>
            </Pressable>
          );
        })}
      </View>

      <Text style={[styles.label, { color: colors.text }]}>{t('search.band_heading')}</Text>
      <View style={styles.pillsRow}>
        {FILTER_BANDS.map((band) => {
          const selected = selectedBand === band;
          const label = t(`risk.${band}`);
          return (
            <Pressable
              key={band}
              accessibilityRole="button"
              accessibilityLabel={label}
              accessibilityState={{ selected }}
              onPress={() => setSelectedBand(selected ? null : band)}
              style={[
                styles.pill,
                {
                  backgroundColor: selected ? colors.primary : colors.surface,
                  borderColor: selected ? colors.primary : colors.border,
                },
              ]}
            >
              <Text style={[styles.pillText, { color: selected ? colors.onPrimary : colors.text }]}>
                {label}
              </Text>
            </Pressable>
          );
        })}
      </View>

      <Text style={[styles.label, { color: colors.text }]}>{t('search.min_score_heading')}</Text>
      <View style={styles.pillsRow}>
        {MIN_SCORES.map((scoreVal) => {
          const selected = minScore === scoreVal;
          const label =
            scoreVal === null
              ? t('search.score_any')
              : scoreVal === 50
                ? t('search.score_50')
                : t('search.score_75');
          return (
            <Pressable
              key={String(scoreVal)}
              accessibilityRole="button"
              accessibilityLabel={label}
              accessibilityState={{ selected }}
              onPress={() => setMinScore(scoreVal)}
              style={[
                styles.pill,
                {
                  backgroundColor: selected ? colors.primary : colors.surface,
                  borderColor: selected ? colors.primary : colors.border,
                },
              ]}
            >
              <Text style={[styles.pillText, { color: selected ? colors.onPrimary : colors.text }]}>
                {label}
              </Text>
            </Pressable>
          );
        })}
      </View>

      <View style={styles.ingredientFiltersRow}>
        <View style={styles.ingredientFilterCol}>
          <Text style={[styles.smallLabel, { color: colors.text }]}>
            {t('search.include_label')}
          </Text>
          <TextInput
            accessibilityLabel={t('search.include_label')}
            onChangeText={setIncludeIngredient}
            placeholder={t('search.include_placeholder')}
            placeholderTextColor={colors.textMuted}
            style={[
              styles.smallInput,
              {
                color: colors.text,
                backgroundColor: colors.surface,
                borderColor: colors.border,
              },
            ]}
            value={includeIngredient}
          />
        </View>
        <View style={styles.ingredientFilterCol}>
          <Text style={[styles.smallLabel, { color: colors.text }]}>
            {t('search.exclude_label')}
          </Text>
          <TextInput
            accessibilityLabel={t('search.exclude_label')}
            onChangeText={setExcludeIngredient}
            placeholder={t('search.exclude_placeholder')}
            placeholderTextColor={colors.textMuted}
            style={[
              styles.smallInput,
              {
                color: colors.text,
                backgroundColor: colors.surface,
                borderColor: colors.border,
              },
            ]}
            value={excludeIngredient}
          />
        </View>
      </View>

      <View style={styles.metaRow}>
        <Text style={[styles.countText, { color: colors.textMuted }]}>
          {t('search.results_count', { count: products.length })}
        </Text>
        <Pressable
          accessibilityRole="button"
          accessibilityLabel={t('search.clear_filters')}
          onPress={handleResetFilters}
          style={[styles.resetButton, { borderColor: colors.border }]}
        >
          <Text style={[styles.resetText, { color: colors.primary }]}>
            {t('search.clear_filters')}
          </Text>
        </Pressable>
      </View>

      {catalogQuery.isPending ? (
        <View style={styles.list}>
          <Skeleton height={116} />
          <Skeleton height={116} />
        </View>
      ) : catalogQuery.isError ? (
        <ErrorState
          onRetry={() => {
            void catalogQuery.refetch();
          }}
        />
      ) : products.length === 0 ? (
        <EmptyState title={t('search.empty_title')} description={t('search.empty_description')} />
      ) : (
        <View style={styles.list}>
          {products.map((product) => (
            <ProductCard
              key={product.id}
              product={product}
              artwork={getProductArtwork(product.category_slug)}
              onPress={(id) =>
                router.push({
                  pathname: '/products/[productId]',
                  params: { productId: id },
                } as unknown as Href)
              }
            />
          ))}
        </View>
      )}
    </Screen>
  );
}

const styles = StyleSheet.create({
  content: { padding: spacing.lg, gap: spacing.md, paddingBottom: spacing.xxxl },
  backButton: {
    minHeight: 44,
    alignSelf: 'flex-start',
    justifyContent: 'center',
    paddingHorizontal: spacing.md,
    borderWidth: 1,
    borderRadius: radii.md,
  },
  backText: {
    fontSize: typography.size.sm,
    fontWeight: typography.weight.semibold,
  },
  title: {
    fontSize: typography.size.xl,
    lineHeight: typography.lineHeight.xl,
    fontWeight: typography.weight.bold,
  },
  searchGroup: {
    gap: spacing.xs,
  },
  label: {
    fontSize: typography.size.sm,
    fontWeight: typography.weight.bold,
  },
  smallLabel: {
    fontSize: typography.size.xs,
    fontWeight: typography.weight.semibold,
  },
  input: {
    minHeight: 48,
    borderWidth: 1,
    borderRadius: radii.md,
    paddingHorizontal: spacing.md,
    fontSize: typography.size.md,
  },
  smallInput: {
    minHeight: 44,
    borderWidth: 1,
    borderRadius: radii.md,
    paddingHorizontal: spacing.sm,
    fontSize: typography.size.sm,
  },
  pillsRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.sm,
  },
  pill: {
    minHeight: 44,
    justifyContent: 'center',
    paddingHorizontal: spacing.md,
    borderWidth: 1,
    borderRadius: radii.pill,
  },
  pillText: {
    fontSize: typography.size.xs,
    fontWeight: typography.weight.semibold,
  },
  ingredientFiltersRow: {
    flexDirection: 'row',
    gap: spacing.sm,
  },
  ingredientFilterCol: {
    flex: 1,
    gap: spacing.xs,
  },
  metaRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: spacing.sm,
  },
  countText: {
    fontSize: typography.size.xs,
    fontWeight: typography.weight.medium,
  },
  resetButton: {
    minHeight: 44,
    justifyContent: 'center',
    paddingHorizontal: spacing.md,
    borderWidth: 1,
    borderRadius: radii.md,
  },
  resetText: {
    fontSize: typography.size.xs,
    fontWeight: typography.weight.semibold,
  },
  list: {
    gap: spacing.md,
  },
});
