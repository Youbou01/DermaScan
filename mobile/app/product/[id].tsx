import { useState } from 'react';
import { View } from 'react-native';
import { Button, FieldError, Tabs } from 'heroui-native';
import { router, useLocalSearchParams } from 'expo-router';
import * as Haptics from 'expo-haptics';
import { useMutation } from '@tanstack/react-query';
import { Screen } from '@/components/Screen';
import { AppText } from '@/components/AppText';
import { ProductPhoto } from '@/components/ProductPhoto';
import { AnalysisScore, Formula } from '@/components/Formula';
import { DataState, LoadingState, SignInGate } from '@/components/DataState';
import {
  useBlacklist,
  useProduct,
  useProfile,
  useSuitability,
  notifySuccess,
  privateKey,
  queryClient,
  useUserId,
} from '@/lib/api/queries';
import { ApiError, errorMessage, request } from '@/lib/api/client';
import type { Ingredient, Profile, ProfileInput } from '@/lib/api/types';
import { colors } from '@/lib/theme';
export default function ProductDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const uid = useUserId();
  const product = useProduct(id);
  const profile = useProfile();
  const blacklist = useBlacklist();
  const [tab, setTab] = useState('ingredients');
  const [selected, setSelected] = useState<Ingredient | null>(null);
  const suitability = useSuitability(id, tab === 'compatibility' && !!profile.data?.skin_type);
  const mutation = useMutation({
    mutationFn: async (action: 'allergy' | 'ingredient' | 'product') => {
      if (action === 'allergy') {
        if (!selected?.ingredient_id) return;
        const current = await request<Profile>('/profile', { auth: true });
        const ids = current.allergy_ingredient_ids.includes(selected.ingredient_id)
          ? current.allergy_ingredient_ids.filter((value) => value !== selected.ingredient_id)
          : [...current.allergy_ingredient_ids, selected.ingredient_id];
        const body: ProfileInput = {
          skin_type: current.skin_type,
          is_pregnant_or_nursing: current.is_pregnant_or_nursing,
          health_conditions: current.health_conditions,
          allergy_ingredient_ids: ids,
        };
        await request('/profile', { method: 'PUT', auth: true, body });
      } else {
        const ingredientId = selected?.ingredient_id;
        const target = action === 'product' ? id : ingredientId;
        if (!target) return;
        const current = await request<{ product_ids: string[]; ingredient_ids: string[] }>(
          '/profile/blacklist',
          { auth: true },
        );
        const isPresent = (
          action === 'product' ? current.product_ids : current.ingredient_ids
        ).includes(target);
        await request(
          '/profile/blacklist/' + (action === 'product' ? 'products/' : 'ingredients/') + target,
          { auth: true, method: isPresent ? 'DELETE' : 'POST' },
        );
      }
    },
    onSuccess: () => {
      notifySuccess();
      void queryClient.invalidateQueries({ queryKey: privateKey('profile', uid) });
      void queryClient.invalidateQueries({ queryKey: privateKey('blacklist', uid) });
      void queryClient.invalidateQueries({ queryKey: ['suitability'] });
      setSelected(null);
    },
  });
  return (
    <Screen title="Product details">
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
        product.data && (
          <>
            <ProductPhoto url={product.data.image_url} name={product.data.name} height={225} />
            <View style={{ gap: 8 }}>
              {!!product.data.brand && (
                <AppText weight="semibold" style={{ fontSize: 12, color: colors.muted }}>
                  {product.data.brand}
                </AppText>
              )}
              <AppText
                weight="semibold"
                style={{ fontSize: 27, lineHeight: 34, letterSpacing: -0.8 }}
              >
                {product.data.name}
              </AppText>
              {product.data.category && (
                <AppText style={{ color: colors.muted }}>{product.data.category.name}</AppText>
              )}
              <AppText style={{ fontSize: 11, color: colors.muted }}>
                {product.data.barcode}
              </AppText>
            </View>
            <AnalysisScore analysis={product.data} />
            <Tabs
              value={tab}
              onValueChange={(value) => {
                setTab(value);
                void Haptics.selectionAsync();
              }}
            >
              <Tabs.List className="w-full">
                <Tabs.Indicator />
                <Tabs.Trigger value="ingredients" className="flex-1">
                  <Tabs.Label numberOfLines={1}>Ingredients</Tabs.Label>
                </Tabs.Trigger>
                <Tabs.Trigger value="compatibility" className="flex-1">
                  <Tabs.Label numberOfLines={1}>For you</Tabs.Label>
                </Tabs.Trigger>
              </Tabs.List>
              <Tabs.Content value="ingredients">
                <View style={{ paddingTop: 22 }}>
                  <Formula
                    analysis={product.data}
                    onEmpty={() => router.push('/analysis')}
                    onChoose={(ingredient) => {
                      setSelected(ingredient);
                      mutation.reset();
                    }}
                  />
                </View>
              </Tabs.Content>
              <Tabs.Content value="compatibility">
                <View style={{ paddingTop: 22, gap: 18 }}>
                  {!uid ? (
                    <SignInGate />
                  ) : profile.isPending ? (
                    <LoadingState />
                  ) : profile.isError ? (
                    <DataState
                      error={profile.error}
                      onAction={() => {
                        void profile.refetch();
                      }}
                    />
                  ) : !profile.data?.skin_type ? (
                    <DataState
                      message="Set your skin profile before checking compatibility."
                      action="Set skin profile"
                      onAction={() => router.push('/profile')}
                    />
                  ) : suitability.isPending ? (
                    <LoadingState />
                  ) : suitability.isError ? (
                    <DataState
                      error={suitability.error}
                      message={
                        suitability.error instanceof ApiError && suitability.error.status === 404
                          ? 'Compatibility is unavailable right now. Please try again later.'
                          : undefined
                      }
                      onAction={() => {
                        void suitability.refetch();
                      }}
                    />
                  ) : (
                    suitability.data && (
                      <>
                        <AppText weight="semibold" style={{ fontSize: 22 }}>
                          {suitability.data.verdict === 'suitable'
                            ? 'No profile alerts found'
                            : suitability.data.verdict === 'avoid'
                              ? 'Avoid for your profile'
                              : 'Use with caution'}
                        </AppText>
                        {suitability.data.alerts.map((alert) => (
                          <View
                            key={JSON.stringify([alert.code, alert.ingredient_name])}
                            style={{
                              gap: 8,
                              paddingVertical: 12,
                              borderTopWidth: 1,
                              borderTopColor: colors.border,
                            }}
                          >
                            <AppText
                              weight="semibold"
                              style={{
                                color: alert.severity === 'high' ? colors.red : colors.orange,
                              }}
                            >
                              {alert.title}
                            </AppText>
                            <AppText style={{ lineHeight: 21 }}>{alert.detail}</AppText>
                          </View>
                        ))}
                        <AppText style={{ color: colors.muted, fontSize: 12, lineHeight: 19 }}>
                          Based on your saved profile and recognized ingredients only. This does not
                          guarantee suitability or safety.
                        </AppText>
                        <Button variant="tertiary" onPress={() => router.push('/profile')}>
                          <Button.Label>Edit skin profile</Button.Label>
                        </Button>
                      </>
                    )
                  )}
                </View>
              </Tabs.Content>
            </Tabs>
            {selected && (
              <View
                style={{ backgroundColor: colors.white, padding: 18, borderRadius: 18, gap: 12 }}
              >
                <AppText weight="semibold">{selected.name}</AppText>
                {!uid ? (
                  <SignInGate message="Sign in to save allergies and ingredients you avoid." />
                ) : (
                  <>
                    <Button
                      isDisabled={mutation.isPending || !profile.data}
                      variant="secondary"
                      onPress={() => mutation.mutate('allergy')}
                    >
                      <Button.Label>
                        {profile.data?.allergy_ingredient_ids.includes(selected.ingredient_id ?? '')
                          ? 'Remove allergy'
                          : 'Save as allergy'}
                      </Button.Label>
                    </Button>
                    <Button
                      isDisabled={mutation.isPending || !blacklist.data}
                      variant="secondary"
                      onPress={() => mutation.mutate('ingredient')}
                    >
                      <Button.Label>
                        {blacklist.data?.ingredient_ids.includes(selected.ingredient_id ?? '')
                          ? 'Stop avoiding ingredient'
                          : 'Avoid ingredient'}
                      </Button.Label>
                    </Button>
                    {profile.isError && (
                      <DataState
                        error={profile.error}
                        onAction={() => {
                          void profile.refetch();
                        }}
                      />
                    )}
                    {blacklist.isError && (
                      <DataState
                        error={blacklist.error}
                        onAction={() => {
                          void blacklist.refetch();
                        }}
                      />
                    )}
                  </>
                )}
                <Button size="sm" variant="tertiary" onPress={() => setSelected(null)}>
                  <Button.Label>Close</Button.Label>
                </Button>
              </View>
            )}
            {mutation.isError && <FieldError>{errorMessage(mutation.error)}</FieldError>}
            <Button
              onPress={() => router.push({ pathname: '/routine/add', params: { productId: id } })}
            >
              <Button.Label>Add to a routine</Button.Label>
            </Button>
            {uid && (
              <Button
                variant="tertiary"
                isDisabled={mutation.isPending || !blacklist.data}
                onPress={() => mutation.mutate('product')}
              >
                <Button.Label>
                  {blacklist.data?.product_ids.includes(id)
                    ? 'Stop avoiding this product'
                    : 'Avoid this product'}
                </Button.Label>
              </Button>
            )}
          </>
        )
      )}
    </Screen>
  );
}
