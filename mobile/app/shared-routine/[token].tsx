import { useState } from 'react';
import { View } from 'react-native';
import { Button, FieldError } from 'heroui-native';
import { useMutation, useQuery } from '@tanstack/react-query';
import { router, useLocalSearchParams } from 'expo-router';
import { useTranslation } from 'react-i18next';
import { AppText } from '@/components/AppText';
import { DataState, LoadingState, SignInGate } from '@/components/DataState';
import { Screen } from '@/components/Screen';
import { ApiError, errorMessage, request } from '@/lib/api/client';
import { notifySuccess, privateKey, queryClient, useUserId } from '@/lib/api/queries';
import type { CopySharedRoutineRequest, Routine, SharedRoutine, Slot } from '@/lib/api/types';
import { confirmedRoutineCopy } from '@/lib/routineShare';
import { colors } from '@/lib/theme';

export default function SharedRoutineScreen() {
  const { token } = useLocalSearchParams<{ token: string }>();
  const { t } = useTranslation();
  const uid = useUserId();
  const [destinationSlot, setDestinationSlot] = useState<Slot | null>(null);
  const shared = useQuery({
    queryKey: ['shared-routine', token],
    enabled: !!token,
    queryFn: ({ signal }) =>
      request<SharedRoutine>(`/routines/shared/${encodeURIComponent(token)}`, { signal }),
  });
  const copy = useMutation({
    mutationFn: async (body: CopySharedRoutineRequest) => {
      return request<Routine>(`/routines/shared/${encodeURIComponent(token)}/copy`, {
        method: 'POST',
        auth: true,
        body,
      });
    },
    onSuccess: () => {
      notifySuccess();
      setDestinationSlot(null);
      void queryClient.invalidateQueries({ queryKey: privateKey('routines', uid) });
    },
  });
  const slotLabel = (slot: Slot) =>
    slot === 'morning' ? t('routineShare.morning') : t('routineShare.evening');

  return (
    <Screen title={t('routineShare.publicTitle')}>
      {shared.isPending ? (
        <LoadingState />
      ) : shared.isError ? (
        <DataState
          error={shared.error}
          message={
            shared.error instanceof ApiError && shared.error.status === 404
              ? t('routineShare.expired')
              : undefined
          }
          onAction={() => {
            void shared.refetch();
          }}
        />
      ) : shared.data ? (
        <>
          <AppText weight="semibold" style={{ fontSize: 27, lineHeight: 34 }}>
            {t('routineShare.publicTitle')}
          </AppText>
          <AppText style={{ color: colors.muted, lineHeight: 21 }}>
            {slotLabel(shared.data.slot)} ·{' '}
            {t('routineShare.expiresAt', {
              date: new Date(shared.data.expires_at).toLocaleDateString(),
            })}
          </AppText>
          <AppText weight="semibold" style={{ fontSize: 20 }}>
            {t('routineShare.steps')}
          </AppText>
          {shared.data.steps.map((step) => (
            <View
              key={`${step.step_order}-${step.product.id}`}
              style={{
                gap: 7,
                paddingVertical: 14,
                borderTopWidth: 1,
                borderTopColor: colors.border,
              }}
            >
              <AppText style={{ color: colors.muted, fontSize: 12 }}>
                {step.step_order}. {step.step_type}
              </AppText>
              <Button
                variant="tertiary"
                style={{ height: 'auto', justifyContent: 'flex-start', paddingHorizontal: 0 }}
                accessibilityLabel={t('routineShare.viewProduct', { name: step.product.name })}
                onPress={() =>
                  router.push({ pathname: '/product/[id]', params: { id: step.product.id } })
                }
              >
                <Button.Label style={{ textAlign: 'left' }}>{step.product.name}</Button.Label>
              </Button>
              {!!step.active_ingredients?.length && (
                <AppText style={{ color: colors.muted, fontSize: 12 }}>
                  {step.active_ingredients?.join(', ')}
                </AppText>
              )}
            </View>
          ))}
          {!uid ? (
            <SignInGate message={t('routineShare.signIn')} />
          ) : (
            <View style={{ gap: 12, paddingTop: 10 }}>
              <AppText weight="semibold" style={{ fontSize: 18 }}>
                {t('routineShare.chooseSlot')}
              </AppText>
              <View style={{ flexDirection: 'row', gap: 10 }}>
                {(['morning', 'evening'] as const).map((slot) => (
                  <Button
                    key={slot}
                    variant={destinationSlot === slot ? 'primary' : 'secondary'}
                    isDisabled={copy.isPending}
                    style={{ flex: 1, minHeight: 48 }}
                    onPress={() => {
                      setDestinationSlot(slot);
                      copy.reset();
                    }}
                  >
                    <Button.Label>{slotLabel(slot)}</Button.Label>
                  </Button>
                ))}
              </View>
              {!!destinationSlot && (
                <>
                  <AppText style={{ lineHeight: 21 }}>
                    {t('routineShare.replaceWarning', {
                      slot: slotLabel(destinationSlot),
                    })}
                  </AppText>
                  <Button
                    isDisabled={copy.isPending}
                    style={{ minHeight: 48 }}
                    onPress={() => {
                      const requestBody = confirmedRoutineCopy(destinationSlot, true);
                      if (requestBody) copy.mutate(requestBody);
                    }}
                  >
                    <Button.Label>
                      {copy.isPending ? t('routineShare.copying') : t('routineShare.confirmCopy')}
                    </Button.Label>
                  </Button>
                  <Button
                    variant="tertiary"
                    isDisabled={copy.isPending}
                    onPress={() => setDestinationSlot(null)}
                  >
                    <Button.Label>{t('routineShare.cancel')}</Button.Label>
                  </Button>
                </>
              )}
              {copy.isError && <FieldError>{errorMessage(copy.error)}</FieldError>}
              {copy.isSuccess && (
                <AppText accessibilityRole="alert" style={{ color: colors.green, lineHeight: 21 }}>
                  {t('routineShare.copied')}
                </AppText>
              )}
            </View>
          )}
        </>
      ) : null}
    </Screen>
  );
}
