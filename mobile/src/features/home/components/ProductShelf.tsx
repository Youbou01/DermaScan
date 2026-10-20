import { memo, useCallback, useMemo, type ReactElement } from 'react';
import { useInfiniteQuery } from '@tanstack/react-query';
import { ActivityIndicator, FlatList, StyleSheet, Text, View } from 'react-native';
import { fetchHomeSection } from '@/api/hooks';
import type { HomeSection, ProductCard as ProductCardData } from '@/api/types';
import { ProductCard, Skeleton } from '@/components';
import { useTranslation } from '@/i18n/useTranslation';
import { spacing, typography, useThemeColors } from '@/theme/tokens';
import { getProductArtwork } from '../product-artwork';

interface ProductShelfProps {
  section: HomeSection;
  onProductPress: (id: string) => void;
}

function ProductShelfView({ section, onProductPress }: ProductShelfProps): ReactElement {
  const colors = useThemeColors();
  const { t } = useTranslation();
  const initialProducts = useMemo(
    () => section.items.filter((item): item is ProductCardData => 'id' in item),
    [section.items],
  );
  const query = useInfiniteQuery({
    queryKey: ['home-section', section.id, section.next_cursor],
    initialPageParam: section.next_cursor,
    enabled: false,
    queryFn: ({ pageParam }) =>
      pageParam ? fetchHomeSection(section.id, pageParam) : Promise.resolve(section),
    getNextPageParam: (lastPage) => lastPage.next_cursor ?? undefined,
  });
  const { data, fetchNextPage, hasNextPage, isFetchingNextPage } = query;
  const products = useMemo(
    () =>
      [...initialProducts, ...(data?.pages.flatMap((page) => page.items) ?? [])].filter(
        (item): item is ProductCardData => 'id' in item,
      ),
    [data?.pages, initialProducts],
  );
  const loadMore = useCallback((): void => {
    if (section.next_cursor && !isFetchingNextPage && (!data || hasNextPage)) {
      void fetchNextPage({ cancelRefetch: false });
    }
  }, [data, fetchNextPage, hasNextPage, isFetchingNextPage, section.next_cursor]);
  const keyExtractor = useCallback((product: ProductCardData): string => product.id, []);
  const renderProduct = useCallback(
    ({ item }: { item: ProductCardData }): ReactElement => (
      <View style={styles.card}>
        <ProductCard
          product={item}
          onPress={onProductPress}
          layout="shelf"
          artwork={getProductArtwork(item.category_slug)}
        />
      </View>
    ),
    [onProductPress],
  );
  const footer = useMemo((): ReactElement | undefined => {
    if (isFetchingNextPage) {
      return (
        <View style={styles.footer}>
          <Skeleton width={72} height={96} />
          <ActivityIndicator
            accessibilityLabel={t('home.skeleton_products')}
            color={colors.primary}
          />
        </View>
      );
    }
    return undefined;
  }, [colors.primary, isFetchingNextPage, t]);

  return (
    <View style={styles.container}>
      <Text accessibilityRole="header" style={[styles.title, { color: colors.text }]}>
        {section.title}
      </Text>
      <FlatList
        testID={`home-shelf-${section.id}`}
        horizontal
        data={products}
        keyExtractor={keyExtractor}
        renderItem={renderProduct}
        onEndReached={loadMore}
        onEndReachedThreshold={0.45}
        ListFooterComponent={footer}
        snapToAlignment="start"
        decelerationRate="fast"
        snapToInterval={228}
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.listContent}
      />
    </View>
  );
}

export const ProductShelf = memo(ProductShelfView);

const styles = StyleSheet.create({
  container: { gap: spacing.md, paddingVertical: spacing.md },
  title: {
    paddingHorizontal: spacing.lg,
    fontSize: typography.size.lg,
    lineHeight: typography.lineHeight.lg,
    fontWeight: '700',
  },
  listContent: { paddingHorizontal: spacing.lg, gap: spacing.md },
  card: { width: 212 },
  footer: {
    width: 100,
    minHeight: 116,
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing.sm,
  },
});
