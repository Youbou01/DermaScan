import { useState } from 'react';
import { View } from 'react-native';
import { Button, FieldError } from 'heroui-native';
import { useMutation, useQuery } from '@tanstack/react-query';
import { router } from 'expo-router';
import * as Haptics from 'expo-haptics';
import { Screen } from '@/components/Screen';
import { AppText } from '@/components/AppText';
import { DataState, LoadingState, SignInGate } from '@/components/DataState';
import { useProfile, useUserId, notifySuccess, privateKey, queryClient } from '@/lib/api/queries';
import { request, errorMessage } from '@/lib/api/client';
import { routineInputs } from '@/lib/routines';
import type { Recommendations, Routine, Slot } from '@/lib/api/types';
import { colors } from '@/lib/theme';
export default function RecommendationsScreen() {
  const uid = useUserId();
  const profile = useProfile();
  const skinType = profile.data?.skin_type;
  const [replaceSlot, setReplaceSlot] = useState<Slot | null>(null);
  const [notice, setNotice] = useState('');
  const result = useQuery({
    queryKey: ['recommendations', uid, skinType],
    enabled: !!uid && !!skinType,
    queryFn: ({ signal }) =>
      request<Recommendations>('/routines/recommendations?skin_type=' + skinType, {
        auth: true,
        signal,
      }),
  });
  const mutation = useMutation({
    mutationFn: async (slot: Slot) => {
      if (!result.data) throw new Error('Refresh recommendations and try again.');
      return request<Routine>(`/routines/${slot}`, {
        method: 'PUT',
        auth: true,
        body: { steps: routineInputs(result.data[slot]) },
      });
    },
    onSuccess: () => {
      notifySuccess();
      setNotice('Routine saved. Review its conflict warnings in Your routines.');
      setReplaceSlot(null);
      void queryClient.invalidateQueries({ queryKey: privateKey('routines', uid) });
    },
  });
  return (
    <Screen title="Recommendations">
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
      ) : !skinType ? (
        <DataState
          message="Set your skin type to find recommendations."
          action="Set skin profile"
          onAction={() => router.push('/profile')}
        />
      ) : (
        <>
          <AppText weight="semibold" style={{ fontSize: 28 }}>
            A starting point for {skinType} skin.
          </AppText>
          <AppText style={{ color: colors.muted, fontSize: 12, lineHeight: 19 }}>
            Suggestions use skin type, not your full allergy or health profile. Check each
            product&apos;s compatibility before using it.
          </AppText>
          {result.isPending ? (
            <LoadingState />
          ) : result.isError ? (
            <DataState
              error={result.error}
              onAction={() => {
                void result.refetch();
              }}
            />
          ) : (
            result.data &&
            (['morning', 'evening'] as const).map((slot) => (
              <View key={slot} style={{ gap: 14 }}>
                <AppText weight="semibold" style={{ fontSize: 22 }}>
                  {slot === 'morning' ? 'Morning' : 'Evening'}
                </AppText>
                {result.data[slot].length ? (
                  <>
                    {result.data[slot].map((step) => (
                      <View
                        key={`${step.step_order}-${step.product.id}`}
                        style={{
                          borderWidth: 1,
                          borderRadius: 20,
                          paddingHorizontal: 16,
                          borderColor: colors.border,
                          paddingVertical: 12,
                          gap: 6,
                        }}
                      >
                        <AppText style={{ fontSize: 12, color: colors.muted }}>
                          {step.step_type}
                        </AppText>
                        <Button
                          variant="tertiary"
                          style={{
                            height: 'auto',
                            justifyContent: 'flex-start',
                            paddingHorizontal: 0,
                          }}
                          onPress={() =>
                            router.push({
                              pathname: '/product/[id]',
                              params: { id: step.product.id },
                            })
                          }
                        >
                          <Button.Label style={{ textAlign: 'left' }}>
                            {step.product.name}
                          </Button.Label>
                        </Button>
                      </View>
                    ))}
                    {replaceSlot === slot ? (
                      <>
                        <AppText>This replaces every step in your {slot} routine.</AppText>
                        <Button
                          isDisabled={mutation.isPending}
                          onPress={() => mutation.mutate(slot)}
                        >
                          <Button.Label>
                            {mutation.isPending ? 'Saving…' : 'Replace routine'}
                          </Button.Label>
                        </Button>
                        <Button
                          variant="tertiary"
                          isDisabled={mutation.isPending}
                          onPress={() => setReplaceSlot(null)}
                        >
                          <Button.Label>Keep my routine</Button.Label>
                        </Button>
                      </>
                    ) : (
                      <Button
                        variant="secondary"
                        isDisabled={mutation.isPending}
                        onPress={() => {
                          setReplaceSlot(slot);
                          setNotice('');
                          void Haptics.selectionAsync();
                        }}
                      >
                        <Button.Label>Use this routine</Button.Label>
                      </Button>
                    )}
                  </>
                ) : (
                  <DataState
                    message="No recommendations available yet."
                    action="Refresh"
                    onAction={() => {
                      void result.refetch();
                    }}
                  />
                )}
              </View>
            ))
          )}
          {mutation.isError && <FieldError>{errorMessage(mutation.error)}</FieldError>}
          {!!notice && <AppText style={{ color: colors.green, lineHeight: 21 }}>{notice}</AppText>}
          <Button variant="tertiary" onPress={() => router.push('/routines')}>
            <Button.Label>Your routines</Button.Label>
          </Button>
        </>
      )}
    </Screen>
  );
}
