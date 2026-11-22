import { FlatList, View } from 'react-native';
import { Button, FieldError } from 'heroui-native';
import { router } from 'expo-router';
import { useMutation } from '@tanstack/react-query';
import Animated, { FadeIn, FadeOut } from 'react-native-reanimated';
import { AppText } from '@/components/AppText';
import { ScreenHeader } from '@/components/Screen';
import { DataState, LoadingState, SignInGate } from '@/components/DataState';
import { colors } from '@/lib/theme';
import {
  useBlacklist,
  useProduct,
  useUserId,
  privateKey,
  queryClient,
  notifySuccess,
} from '@/lib/api/queries';
import { request, errorMessage } from '@/lib/api/client';
function AvoidedProduct({ id }: { id: string }) {
  const product = useProduct(id);
  const uid = useUserId();
  const mutation = useMutation({
    mutationFn: () =>
      request('/profile/blacklist/products/' + id, { method: 'DELETE', auth: true }),
    onSuccess: () => {
      notifySuccess();
      void queryClient.invalidateQueries({ queryKey: privateKey('blacklist', uid) });
      void queryClient.invalidateQueries({ queryKey: privateKey('profile', uid) });
      void queryClient.invalidateQueries({ queryKey: ['suitability'] });
    },
  });
  return (
    <Animated.View
      entering={FadeIn}
      exiting={FadeOut}
      style={{
        borderBottomWidth: 1,
        borderBottomColor: colors.border,
        paddingVertical: 18,
        gap: 12,
      }}
    >
      {product.isPending ? (
        <LoadingState />
      ) : product.isError ? (
        <DataState
          error={product.error}
          onAction={() => {
            void product.refetch();
          }}
        />
      ) : (
        <Button
          variant="tertiary"
          onPress={() => router.push({ pathname: '/product/[id]', params: { id } })}
          style={{ height: 'auto' }}
        >
          <Button.Label>{product.data?.name}</Button.Label>
        </Button>
      )}
      <Button
        size="sm"
        variant="secondary"
        isDisabled={mutation.isPending}
        onPress={() => mutation.mutate()}
      >
        <Button.Label>{mutation.isPending ? 'Removing…' : 'Stop avoiding'}</Button.Label>
      </Button>
      {mutation.isError && <FieldError>{errorMessage(mutation.error)}</FieldError>}
    </Animated.View>
  );
}
export default function AvoidanceScreen() {
  const uid = useUserId();
  const result = useBlacklist();
  return (
    <View style={{ flex: 1, backgroundColor: colors.background }}>
      <ScreenHeader title="Products you avoid" />
      <FlatList
        data={result.data?.product_ids ?? []}
        keyExtractor={(id) => id}
        contentContainerStyle={{ padding: 22, paddingBottom: 40 }}
        renderItem={({ item }) => <AvoidedProduct id={item} />}
        ListHeaderComponent={
          <AppText weight="semibold" style={{ fontSize: 28, marginBottom: 16 }}>
            Your no-thanks list.
          </AppText>
        }
        ListEmptyComponent={
          !uid ? (
            <SignInGate />
          ) : result.isPending ? (
            <LoadingState />
          ) : result.isError ? (
            <DataState
              error={result.error}
              onAction={() => {
                void result.refetch();
              }}
            />
          ) : (
            <DataState
              message="Products you choose to avoid will appear here."
              action="Find a product"
              onAction={() => router.push('/')}
            />
          )
        }
        ListFooterComponent={
          result.data?.ingredient_ids.length ? (
            <View style={{ paddingTop: 24, gap: 8 }}>
              <AppText weight="medium">
                {result.data.ingredient_ids.length} avoided{' '}
                {result.data.ingredient_ids.length === 1 ? 'ingredient' : 'ingredients'}
              </AppText>
              <AppText style={{ color: colors.muted, fontSize: 12, lineHeight: 19 }}>
                Manage avoided ingredients from a product&apos;s ingredient explanation.
              </AppText>
            </View>
          ) : undefined
        }
      />
    </View>
  );
}
