import type { ReactElement } from 'react';
import { useMemo } from 'react';
import { FlatList, Pressable, StyleSheet, Text, View, useWindowDimensions } from 'react-native';
import { useProductListQuery } from '@/api/product-list';
import type { ProductCard as ProductCardData } from '@/api/types';
import { useTranslation } from '@/i18n/useTranslation';
import { radii, spacing, typography, useThemeColors } from '@/theme/tokens';
import { EmptyState } from './EmptyState';
import { ErrorState } from './ErrorState';
import { ProductCard } from './ProductCard';
import { Skeleton } from './Skeleton';

export interface ProductListProps {
  /** Name search (2+ characters). Wins over `category`. */
  query?: string;
  /** Category slug. */
  category?: string;
  pageSize?: number;
  onProductPress?: (id: string) => void;
}

const SKELETON_ROWS = 4;
const SKELETON_HEIGHT = 116;

/** Two columns in landscape, one in portrait. */
export function columnsForWindow(width: number, height: number): 1 | 2 {
  return width > height ? 2 : 1;
}

function uniqueProducts(products: ProductCardData[]): ProductCardData[] {
  const seen = new Set<string>();
  return products.filter((product) => {
    if (seen.has(product.id)) {
      return false;
    }
    seen.add(product.id);
    return true;
  });
}

/** Paginated product list. Put it in a `<Screen scroll={false}>`: the list scrolls itself. */
export function ProductList({
  query,
  category,
  pageSize,
  onProductPress,
}: ProductListProps): ReactElement {
  const { t } = useTranslation();
  const colors = useThemeColors();
  const { width, height } = useWindowDimensions();
  const columns = columnsForWindow(width, height);
  const list = useProductListQuery({ query, category }, pageSize);
  const products = useMemo(
    () => uniqueProducts(list.data?.pages.flatMap((page) => page.items) ?? []),
    [list.data],
  );

  if (list.isPending) {
    return (
      <View style={styles.skeletons}>
        {Array.from({ length: SKELETON_ROWS }, (_, row) => (
          <Skeleton key={`skeleton-${row}`} height={SKELETON_HEIGHT} />
        ))}
      </View>
    );
  }
  if (list.isError && products.length === 0) {
    return (
      <ErrorState
        onRetry={() => {
          void list.refetch();
        }}
      />
    );
  }
  if (products.length === 0) {
    return (
      <EmptyState
        title={t('productList.empty_title')}
        description={t('productList.empty_description')}
      />
    );
  }

  let footer: ReactElement | undefined;
  if (list.isFetchingNextPage) {
    footer = <Skeleton height={SKELETON_HEIGHT} />;
  } else if (list.isFetchNextPageError) {
    footer = (
      <View style={styles.footer}>
        <Text style={[styles.footerText, { color: colors.textMuted }]}>
          {t('productList.load_more_failed')}
        </Text>
        <Pressable
          accessibilityRole="button"
          onPress={() => {
            void list.fetchNextPage();
          }}
          style={({ pressed }) => [
            styles.retry,
            { backgroundColor: colors.primary, opacity: pressed ? 0.75 : 1 },
          ]}
        >
          <Text style={[styles.retryText, { color: colors.onPrimary }]}>{t('common.retry')}</Text>
        </Pressable>
      </View>
    );
  }

  return (
    <FlatList
      testID="product-list"
      data={products}
      keyExtractor={(item) => item.id}
      key={`columns-${columns}`}
      numColumns={columns}
      columnWrapperStyle={columns > 1 ? styles.row : undefined}
      renderItem={({ item }) => (
        <View style={columns > 1 ? styles.cell : undefined}>
          <ProductCard product={item} onPress={onProductPress} />
        </View>
      )}
      contentContainerStyle={styles.content}
      onEndReachedThreshold={0.5}
      onEndReached={() => {
        if (list.hasNextPage && !list.isFetchingNextPage && !list.isFetchNextPageError) {
          void list.fetchNextPage();
        }
      }}
      ListFooterComponent={footer}
    />
  );
}

const styles = StyleSheet.create({
  skeletons: { gap: spacing.md, padding: spacing.md },
  content: { gap: spacing.md, padding: spacing.md },
  row: { gap: spacing.md },
  cell: { flex: 1 },
  footer: { alignItems: 'center', gap: spacing.md, padding: spacing.md },
  footerText: { fontSize: typography.size.sm, lineHeight: typography.lineHeight.sm },
  retry: {
    minWidth: 120,
    minHeight: 44,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: spacing.xl,
    borderRadius: radii.md,
  },
  retryText: { fontSize: typography.size.md, fontWeight: typography.weight.semibold },
});
