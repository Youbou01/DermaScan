import { useTranslation } from 'react-i18next';
import { FieldError } from 'heroui-native';
import { useMutation } from '@tanstack/react-query';
import { AppText } from '@/components/AppText';
import { DataState, LoadingState, SignInGate } from '@/components/DataState';
import { LibraryProductRow } from '@/components/LibraryProductRow';
import { ScreenList } from '@/components/ScreenList';
import {
  notifySuccess,
  privateKey,
  queryClient,
  useSavedProducts,
  useUserId,
} from '@/lib/api/queries';
import { errorMessage, request } from '@/lib/api/client';
import type { ProductCard } from '@/lib/api/types';
import { colors } from '@/lib/theme';

export default function SavedProductsScreen() {
  const { t } = useTranslation();
  const uid = useUserId();
  const result = useSavedProducts();
  const products = result.data?.pages.flatMap((page) => page.items) ?? [];
  const remove = useMutation({
    mutationFn: (productId: string) =>
      request(`/library/saved/${encodeURIComponent(productId)}`, {
        method: 'DELETE',
        auth: true,
      }),
    onSuccess: () => {
      notifySuccess();
      void queryClient.invalidateQueries({ queryKey: privateKey('library-saved', uid) });
      void queryClient.invalidateQueries({ queryKey: privateKey('library-saved-status', uid) });
    },
  });

  return (
    <ScreenList<ProductCard>
      title={t('library.savedTitle')}
      data={products}
      keyExtractor={(product) => product.id}
      renderItem={({ item }) => (
        <LibraryProductRow
          product={item}
          actionLabel={remove.isPending ? t('library.removing') : t('library.unsave')}
          isDisabled={remove.isPending}
          onAction={() => remove.mutate(item.id)}
        />
      )}
      onEndReached={() => {
        if (result.hasNextPage && !result.isFetchingNextPage) void result.fetchNextPage();
      }}
      onEndReachedThreshold={0.4}
      ListHeaderComponent={
        uid ? (
          <AppText weight="semibold" style={{ fontSize: 26, marginBottom: 12 }}>
            {t('library.savedHeading')}
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
            message={t('library.emptySaved')}
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
        ) : remove.isError ? (
          <FieldError>{errorMessage(remove.error)}</FieldError>
        ) : (
          <AppText style={{ paddingTop: 12, color: colors.muted, fontSize: 11 }}>
            {t('library.savedTitle')}
          </AppText>
        )
      }
    />
  );
}
