import { useCallback, useMemo, useRef, type ReactElement } from 'react';
import { FlatList, Pressable, RefreshControl, StyleSheet, Text, View } from 'react-native';
import { useQueryClient, type QueryClient } from '@tanstack/react-query';
import { useRouter, type Href } from 'expo-router';
import type { HomeSection } from '@/api/types';
import { useHomeQuery } from '@/api/hooks';
import { EmptyState, ErrorState, Screen, Skeleton } from '@/components';
import { spacing, typography, useThemeColors } from '@/theme/tokens';
import { useTranslation } from '@/i18n/useTranslation';
import { CategoryGrid } from './components/CategoryGrid';
import { ProductShelf } from './components/ProductShelf';

export async function refreshHomeFeed(
  queryClient: QueryClient,
  refetchHome: () => Promise<unknown>,
): Promise<void> {
  queryClient.removeQueries({ queryKey: ['home-section'] });
  await refetchHome();
}

export function HomeScreen(): ReactElement {
  const query = useHomeQuery();
  const refetchHome = query.refetch;
  const queryClient = useQueryClient();
  const router = useRouter();
  const { t } = useTranslation();
  const lastProductNavigation = useRef(0);
  const lastCategoryNavigation = useRef(0);
  const sections = query.data?.sections ?? [];

  const onRefresh = useCallback(async (): Promise<void> => {
    await refreshHomeFeed(queryClient, refetchHome);
  }, [queryClient, refetchHome]);

  const openProduct = useCallback(
    (id: string): void => {
      const now = Date.now();
      if (now - lastProductNavigation.current < 500) return;
      lastProductNavigation.current = now;
      router.push({
        pathname: '/products/[productId]',
        params: { productId: id },
      } as unknown as Href);
    },
    [router],
  );

  const openCategory = useCallback(
    (slug: string): void => {
      const now = Date.now();
      if (now - lastCategoryNavigation.current < 500) return;
      lastCategoryNavigation.current = now;
      router.push({ pathname: '/products', params: { category: slug } } as unknown as Href);
    },
    [router],
  );

  const keyExtractor = useCallback((section: HomeSection): string => section.id, []);
  const renderSection = useCallback(
    ({ item }: { item: HomeSection }): ReactElement | null => {
      if (item.type === 'category_grid') {
        return <CategoryGrid section={item} onCategoryPress={openCategory} />;
      }
      if (item.type === 'top_rated' || item.type === 'recently_added') {
        return <ProductShelf section={item} onProductPress={openProduct} />;
      }
      return null;
    },
    [openCategory, openProduct],
  );
  const contentContainerStyle = useMemo(
    () => [styles.listContent, sections.length === 0 && styles.emptyContent],
    [sections.length],
  );

  if (query.isPending) {
    return (
      <Screen scroll={false}>
        <LoadingFeed />
      </Screen>
    );
  }
  if (query.isError && !query.data) {
    return (
      <Screen scroll={false}>
        <ErrorState onRetry={() => void refetchHome()} />
      </Screen>
    );
  }
  if (sections.length === 0) {
    return (
      <Screen scroll={false}>
        <FlatList
          testID="home-feed"
          data={[]}
          renderItem={() => null}
          refreshControl={
            <RefreshControl
              testID="home-refresh"
              refreshing={query.isRefetching}
              onRefresh={onRefresh}
            />
          }
          ListEmptyComponent={
            <EmptyState title={t('home.empty_title')} description={t('home.empty_description')} />
          }
          contentContainerStyle={styles.emptyContent}
        />
      </Screen>
    );
  }

  return (
    <Screen scroll={false}>
      <FlatList
        testID="home-feed"
        data={sections}
        ListHeaderComponent={<HomeHero />}
        keyExtractor={keyExtractor}
        renderItem={renderSection}
        contentContainerStyle={contentContainerStyle}
        refreshControl={
          <RefreshControl
            testID="home-refresh"
            refreshing={query.isRefetching}
            onRefresh={onRefresh}
          />
        }
        showsVerticalScrollIndicator={false}
      />
    </Screen>
  );
}

function HomeHero(): ReactElement {
  const colors = useThemeColors();
  const router = useRouter();
  const { t } = useTranslation();
  const foreground = colors.onPrimary;
  return (
    <View style={[styles.hero, { backgroundColor: colors.primary }]}>
      <View style={styles.heroMark}>
        <Text style={[styles.heroMarkText, { color: foreground }]}>DS</Text>
      </View>
      <Text style={[styles.heroEyebrow, { color: foreground }]}>{t('home.hero_eyebrow')}</Text>
      <Text accessibilityRole="header" style={[styles.heroTitle, { color: foreground }]}>
        {t('home.hero_title')}
      </Text>
      <Text style={[styles.heroDescription, { color: foreground }]}>
        {t('home.hero_description')}
      </Text>
      <Pressable
        accessibilityRole="button"
        onPress={() => router.push('/scan' as unknown as Href)}
        style={({ pressed }) => [
          styles.scanButton,
          { backgroundColor: colors.onPrimary, opacity: pressed ? 0.8 : 1 },
        ]}
      >
        <Text style={[styles.scanButtonText, { color: colors.primary }]}>
          {t('scan.scan_button')}
        </Text>
      </Pressable>
    </View>
  );
}

function LoadingFeed(): ReactElement {
  return (
    <View style={styles.loading}>
      <View style={styles.categorySkeletons}>
        {Array.from({ length: 4 }, (_, index) => (
          <Skeleton key={`category-${index}`} height={74} width="48%" />
        ))}
      </View>
      {[0, 1].map((section) => (
        <View key={`shelf-${section}`} style={styles.skeletonShelf}>
          <Skeleton height={22} width="40%" />
          <View style={styles.skeletonCards}>
            {[0, 1].map((card) => (
              <Skeleton key={`card-${card}`} height={116} width={260} />
            ))}
          </View>
        </View>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  listContent: { paddingBottom: spacing.xxl },
  emptyContent: { flexGrow: 1, justifyContent: 'center' },
  loading: { gap: spacing.xl, paddingVertical: spacing.lg },
  hero: {
    minHeight: 236,
    marginHorizontal: spacing.lg,
    marginTop: spacing.md,
    marginBottom: spacing.lg,
    padding: spacing.xl,
    borderRadius: 26,
    overflow: 'hidden',
    justifyContent: 'flex-end',
  },
  heroMark: {
    position: 'absolute',
    top: spacing.xl,
    right: spacing.xl,
    width: 48,
    height: 48,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 24,
    backgroundColor: '#FFFFFF24',
  },
  heroMarkText: { fontSize: typography.size.sm, fontWeight: '700' },
  heroEyebrow: {
    marginBottom: spacing.sm,
    fontSize: typography.size.xs,
    fontWeight: '700',
    letterSpacing: 1.2,
    textTransform: 'uppercase',
  },
  heroTitle: {
    maxWidth: 280,
    fontSize: typography.size.xl,
    lineHeight: typography.lineHeight.xl,
    fontWeight: '700',
  },
  heroDescription: {
    maxWidth: 280,
    marginTop: spacing.sm,
    fontSize: typography.size.sm,
    lineHeight: typography.lineHeight.sm,
  },
  scanButton: {
    minHeight: 44,
    alignSelf: 'flex-start',
    justifyContent: 'center',
    marginTop: spacing.lg,
    paddingHorizontal: spacing.lg,
    borderRadius: 12,
  },
  scanButtonText: { fontSize: typography.size.sm, fontWeight: typography.weight.semibold },
  categorySkeletons: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
    gap: spacing.md,
    paddingHorizontal: spacing.lg,
  },
  skeletonShelf: { gap: spacing.md, paddingLeft: spacing.lg },
  skeletonCards: { flexDirection: 'row', gap: spacing.md },
});
