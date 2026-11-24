import { useTranslation } from 'react-i18next';
import { AppText } from '@/components/AppText';
import { DataState, LoadingState, SignInGate } from '@/components/DataState';
import { LibraryProductRow } from '@/components/LibraryProductRow';
import { ScreenList } from '@/components/ScreenList';
import { useRecentlyViewed, useUserId } from '@/lib/api/queries';
import type { ProductCard } from '@/lib/api/types';

export default function RecentlyViewedScreen() {
  const { t } = useTranslation();
  const uid = useUserId();
  const result = useRecentlyViewed();
  const products = result.data?.pages.flatMap((page) => page.items) ?? [];

  return (
    <ScreenList<ProductCard>
      title={t('library.recentTitle')}
      data={products}
      keyExtractor={(product) => product.id}
      renderItem={({ item }) => <LibraryProductRow product={item} />}
      onEndReached={() => {
        if (result.hasNextPage && !result.isFetchingNextPage) void result.fetchNextPage();
      }}
      onEndReachedThreshold={0.4}
      ListHeaderComponent={
        uid ? (
          <AppText weight="semibold" style={{ fontSize: 26, marginBottom: 12 }}>
            {t('library.recentHeading')}
          </AppText>
        ) : undefined
      }
      ListEmptyComponent={
        !uid ? (
          <SignInGate message={t('library.signIn')} />
        ) : result.isPending ? (
          <LoadingState />
        ) : result.isError ? (
          <DataState
            error={result.error}
            action={t('library.retry')}
            onAction={() => {
              void result.refetch();
            }}
          />
        ) : (
          <DataState
            message={t('library.emptyRecent')}
            action={t('library.browse')}
            onAction={() => {
              void import('expo-router').then(({ router }) => router.push('/'));
            }}
          />
        )
      }
      ListFooterComponent={
        result.isFetchingNextPage ? (
          <LoadingState />
        ) : result.isError && products.length > 0 ? (
          <DataState
            error={result.error}
            action={t('library.retry')}
            onAction={() => {
              if (result.hasNextPage) void result.fetchNextPage();
              else void result.refetch();
            }}
          />
        ) : undefined
      }
    />
  );
}
