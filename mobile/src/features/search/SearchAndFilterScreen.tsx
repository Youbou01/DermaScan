import { useEffect, useMemo, useState, type ReactElement } from 'react';
import {
  ActivityIndicator,
  FlatList,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import type { ProductCard as ProductCardData } from '@/api/types';
import {
  useCategoriesQuery,
  useProductSearchInfiniteQuery,
  type ProductFilterParams,
} from '@/api/hooks';
import { EmptyState, ErrorState, ProductCard, Screen, Skeleton } from '@/components';
import { useTranslation } from '@/i18n/useTranslation';
import { getLocalizedCategory } from '@/i18n/category';
import { spacing, typography, useThemeColors } from '@/theme/tokens';

const bands = ['low', 'moderate', 'high'] as const;

export function SearchAndFilterScreen(): ReactElement {
  const params = useLocalSearchParams<{ category?: string | string[] }>();
  const router = useRouter();
  const { t } = useTranslation();
  const colors = useThemeColors();
  const categoryParam = Array.isArray(params.category) ? params.category[0] : params.category;
  const [text, setText] = useState('');
  const [debouncedText, setDebouncedText] = useState('');
  const [categoryOverride, setCategoryOverride] = useState<string | null | undefined>(undefined);
  const category = categoryOverride === undefined ? categoryParam : categoryOverride;
  const [selectedBands, setSelectedBands] = useState<ProductFilterParams['band']>([]);
  const [include, setInclude] = useState<string[]>([]);
  const [exclude, setExclude] = useState<string[]>([]);
  const [ingredientText, setIngredientText] = useState('');
  const [ingredientMode, setIngredientMode] = useState<'include' | 'exclude'>('include');
  const categoryQuery = useCategoriesQuery();
  const filters = useMemo<ProductFilterParams>(
    () => ({ category: category ?? undefined, band: selectedBands, include, exclude }),
    [category, selectedBands, include, exclude],
  );
  const hasFilters = Boolean(category || selectedBands?.length || include.length || exclude.length);
  const query = useProductSearchInfiniteQuery(debouncedText, filters);

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedText(text.trim()), 300);
    return () => clearTimeout(timer);
  }, [text]);

  const rawProducts = query.data?.pages.flatMap((page) => page.items) ?? [];
  const products: ProductCardData[] = rawProducts.map((item) => ({
    id: item.id,
    name: item.name,
    brand: item.brand,
    image_url: item.image_url,
    score: item.score,
    score_band: item.score_band,
    score_is_estimated: false,
    category_slug: null,
  }));

  function toggleBand(band: (typeof bands)[number]): void {
    setSelectedBands((current) =>
      current?.includes(band)
        ? current.filter((item) => item !== band)
        : [...(current ?? []), band],
    );
  }
  function addIngredient(): void {
    const value = ingredientText.trim();
    if (!value) return;
    if (ingredientMode === 'include' && !include.includes(value))
      setInclude((items) => [...items, value]);
    if (ingredientMode === 'exclude' && !exclude.includes(value))
      setExclude((items) => [...items, value]);
    setIngredientText('');
  }
  function removeIngredient(mode: 'include' | 'exclude', value: string): void {
    if (mode === 'include') setInclude((items) => items.filter((item) => item !== value));
    else setExclude((items) => items.filter((item) => item !== value));
  }

  const header = (
    <View style={styles.header}>
      <Text accessibilityRole="header" style={[styles.heading, { color: colors.text }]}>
        {t('search.title')}
      </Text>
      <TextInput
        accessibilityLabel={t('search.placeholder')}
        placeholder={t('search.placeholder')}
        value={text}
        onChangeText={setText}
        returnKeyType="search"
        style={[
          styles.input,
          { color: colors.text, borderColor: colors.border, backgroundColor: colors.surface },
        ]}
      />
      <Text accessibilityRole="header" style={[styles.sectionTitle, { color: colors.text }]}>
        {t('search.categories')}
      </Text>
      <View style={styles.chips}>
        <Chip
          label={t('search.all_categories')}
          selected={!category}
          onPress={() => setCategoryOverride(null)}
        />
        {(categoryQuery.data ?? [])
          .flatMap((parent) => parent.children ?? [])
          .map((item) => (
            <Chip
              key={item.slug}
              label={getLocalizedCategory(item)}
              selected={category === item.slug}
              onPress={() => setCategoryOverride(item.slug)}
            />
          ))}
      </View>
      <Text accessibilityRole="header" style={[styles.sectionTitle, { color: colors.text }]}>
        {t('search.risk_bands')}
      </Text>
      <View style={styles.chips}>
        {bands.map((band) => (
          <Chip
            key={band}
            label={t(`risk.${band}`)}
            selected={selectedBands?.includes(band) ?? false}
            onPress={() => toggleBand(band)}
          />
        ))}
      </View>
      <View style={styles.ingredientRow}>
        <Chip
          label={t('search.include')}
          selected={ingredientMode === 'include'}
          onPress={() => setIngredientMode('include')}
        />
        <Chip
          label={t('search.avoid')}
          selected={ingredientMode === 'exclude'}
          onPress={() => setIngredientMode('exclude')}
        />
      </View>
      <View style={styles.ingredientRow}>
        <TextInput
          accessibilityLabel={t('search.ingredient_placeholder')}
          placeholder={t('search.ingredient_placeholder')}
          value={ingredientText}
          onChangeText={setIngredientText}
          onSubmitEditing={addIngredient}
          returnKeyType="done"
          style={[
            styles.ingredientInput,
            { color: colors.text, borderColor: colors.border, backgroundColor: colors.surface },
          ]}
        />
        <Pressable
          accessibilityRole="button"
          accessibilityLabel={t('search.add')}
          onPress={addIngredient}
          style={[styles.addButton, { backgroundColor: colors.primary }]}
        >
          <Text style={{ color: colors.onPrimary }}>{t('search.add')}</Text>
        </Pressable>
      </View>
      <View style={styles.chips}>
        {include.map((item) => (
          <Chip
            key={`i-${item}`}
            label={`+ ${item}`}
            selected
            onPress={() => removeIngredient('include', item)}
            accessibilityLabel={t('search.remove_filter', { name: item })}
          />
        ))}
        {exclude.map((item) => (
          <Chip
            key={`e-${item}`}
            label={`− ${item}`}
            selected
            onPress={() => removeIngredient('exclude', item)}
            accessibilityLabel={t('search.remove_filter', { name: item })}
          />
        ))}
      </View>
      {debouncedText.length > 0 && debouncedText.length < 2 ? (
        <Text style={{ color: colors.textMuted }}>{t('search.search_hint')}</Text>
      ) : null}
    </View>
  );

  if (query.isPending && rawProducts.length === 0 && (debouncedText.length >= 2 || hasFilters)) {
    return (
      <Screen>
        {header}
        <View style={styles.loading}>
          <Text
            accessibilityRole="text"
            accessibilityLabel={t('search.loading')}
            style={{ color: colors.textMuted }}
          >
            {t('search.loading')}
          </Text>
          <Skeleton height={112} />
          <Skeleton height={112} />
          <Skeleton height={112} />
        </View>
      </Screen>
    );
  }
  if (query.isError && !query.data)
    return (
      <Screen>
        {header}
        <ErrorState onRetry={() => void query.refetch()} />
      </Screen>
    );

  return (
    <Screen scroll={false}>
      <FlatList
        data={products}
        keyExtractor={(item) => item.id}
        ListHeaderComponent={header}
        renderItem={({ item }) => (
          <ProductCard
            product={item}
            onPress={(id) =>
              router.push({ pathname: '/products/[productId]', params: { productId: id } })
            }
          />
        )}
        contentContainerStyle={styles.list}
        ItemSeparatorComponent={() => <View style={{ height: spacing.md }} />}
        ListEmptyComponent={
          debouncedText.length < 2 && !hasFilters ? (
            <View />
          ) : (
            <EmptyState
              title={t('search.empty_title')}
              description={t('search.empty_description')}
            />
          )
        }
        onEndReached={() => {
          if (query.hasNextPage && !query.isFetchingNextPage) void query.fetchNextPage();
        }}
        onEndReachedThreshold={0.4}
        ListFooterComponent={
          query.isFetchingNextPage ? (
            <ActivityIndicator accessibilityLabel={t('search.loading')} />
          ) : (
            <View />
          )
        }
        keyboardShouldPersistTaps="handled"
      />
    </Screen>
  );
}

interface ChipProps {
  label: string;
  selected: boolean;
  onPress: () => void;
  accessibilityLabel?: string;
}
function Chip({ label, selected, onPress, accessibilityLabel }: ChipProps): ReactElement {
  const colors = useThemeColors();
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ selected }}
      accessibilityLabel={accessibilityLabel ?? label}
      onPress={onPress}
      style={[
        styles.chip,
        {
          backgroundColor: selected ? colors.primary : colors.surface,
          borderColor: selected ? colors.primary : colors.border,
        },
      ]}
    >
      <Text style={{ color: selected ? colors.onPrimary : colors.text }}>{label}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  list: { padding: spacing.lg, paddingBottom: spacing.xxxl },
  header: { gap: spacing.md, paddingBottom: spacing.lg },
  heading: {
    fontSize: typography.size.xl,
    lineHeight: typography.lineHeight.xl,
    fontWeight: typography.weight.bold,
  },
  sectionTitle: {
    fontSize: typography.size.md,
    lineHeight: typography.lineHeight.md,
    fontWeight: typography.weight.semibold,
  },
  input: {
    minHeight: 48,
    borderWidth: 1,
    borderRadius: 12,
    paddingHorizontal: spacing.md,
    fontSize: typography.size.md,
  },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm },
  chip: {
    minHeight: 44,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: spacing.md,
    borderWidth: 1,
    borderRadius: 999,
  },
  ingredientRow: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm },
  ingredientInput: {
    minHeight: 44,
    flex: 1,
    borderWidth: 1,
    borderRadius: 10,
    paddingHorizontal: spacing.md,
  },
  addButton: {
    minHeight: 44,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: spacing.md,
    borderRadius: 10,
  },
  loading: { gap: spacing.md, padding: spacing.lg },
});
