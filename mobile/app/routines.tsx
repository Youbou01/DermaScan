import { useState } from 'react';
import { Share, View } from 'react-native';
import { Button, Input, FieldError, Label } from 'heroui-native';
import { router } from 'expo-router';
import * as Linking from 'expo-linking';
import { useMutation } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import Animated, { FadeIn, FadeOut } from 'react-native-reanimated';
import * as Haptics from 'expo-haptics';
import { ScreenList } from '@/components/ScreenList';
import { AppText } from '@/components/AppText';
import { Conflicts } from '@/components/Conflicts';
import { DataState, LoadingState, SignInGate } from '@/components/DataState';
import {
  useRoutines,
  useRoutineShareLinks,
  useUserId,
  notifySuccess,
  queryClient,
  privateKey,
} from '@/lib/api/queries';
import { errorMessage, request } from '@/lib/api/client';
import { routineInputs, findRoutine } from '@/lib/routines';
import { sharedRoutinePath } from '@/lib/routineShare';
import type { Routine, RoutineShare, RoutineStep, Slot } from '@/lib/api/types';
import { colors } from '@/lib/theme';
function StepRow({
  step,
  index,
  count,
  pending,
  onChange,
}: {
  step: RoutineStep;
  index: number;
  count: number;
  pending: boolean;
  onChange: (action: 'up' | 'down' | 'remove' | 'notes', productId: string, notes?: string) => void;
}) {
  const [notes, setNotes] = useState(step.notes ?? '');
  return (
    <Animated.View
      entering={FadeIn}
      exiting={FadeOut}
      style={{ paddingVertical: 18, borderTopWidth: 1, borderTopColor: colors.border, gap: 12 }}
    >
      <View style={{ flexDirection: 'row', alignItems: 'flex-start', gap: 12 }}>
        <AppText weight="semibold" style={{ fontSize: 20, width: 22 }}>
          {index + 1}
        </AppText>
        <View style={{ flex: 1, gap: 4 }}>
          <AppText style={{ fontSize: 12, color: colors.muted }}>
            {step.step_type.charAt(0).toUpperCase() + step.step_type.slice(1)}
          </AppText>
          <Button
            variant="tertiary"
            style={{ height: 'auto', padding: 0, justifyContent: 'flex-start' }}
            onPress={() =>
              router.push({ pathname: '/product/[id]', params: { id: step.product.id } })
            }
          >
            <Button.Label style={{ textAlign: 'left' }}>{step.product.name}</Button.Label>
          </Button>
          {!!step.active_ingredients.length && (
            <AppText style={{ color: colors.muted, fontSize: 11 }}>
              {step.active_ingredients.join(', ')}
            </AppText>
          )}
        </View>
      </View>
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 6 }}>
        <Button
          size="sm"
          variant="tertiary"
          isDisabled={pending || index === 0}
          onPress={() => onChange('up', step.product.id)}
        >
          <Button.Label>Earlier</Button.Label>
        </Button>
        <Button
          size="sm"
          variant="tertiary"
          isDisabled={pending || index === count - 1}
          onPress={() => onChange('down', step.product.id)}
        >
          <Button.Label>Later</Button.Label>
        </Button>
        <Button
          size="sm"
          variant="tertiary"
          isDisabled={pending}
          onPress={() => onChange('remove', step.product.id)}
        >
          <Button.Label>Remove</Button.Label>
        </Button>
      </View>
      <Label>Notes</Label>
      <Input
        value={notes}
        onChangeText={setNotes}
        maxLength={500}
        accessibilityLabel={`Notes for ${step.product.name}`}
      />
      <Button
        size="sm"
        variant="secondary"
        isDisabled={pending || notes === (step.notes ?? '')}
        onPress={() => onChange('notes', step.product.id, notes)}
      >
        <Button.Label>Save notes</Button.Label>
      </Button>
    </Animated.View>
  );
}
export default function RoutinesScreen() {
  const { t } = useTranslation();
  const uid = useUserId();
  const result = useRoutines();
  const [slot, setSlot] = useState<Slot>('morning');
  const shareLinks = useRoutineShareLinks(slot);
  const [notice, setNotice] = useState('');
  const routine = findRoutine(result.data?.routines ?? [], slot);
  const mutation = useMutation({
    mutationFn: async ({
      action,
      productId,
      notes,
    }: {
      action: 'up' | 'down' | 'remove' | 'notes' | 'complete';
      productId?: string;
      notes?: string;
    }) => {
      if (action === 'complete')
        return request<Routine>(`/routines/${slot}/complete`, { auth: true, method: 'POST' });
      const fresh = await request<{ routines: Routine[] }>('/routines', { auth: true });
      let steps = [...(findRoutine(fresh.routines, slot)?.steps ?? [])];
      const index = steps.findIndex((step) => step.product.id === productId);
      if (index === -1)
        throw new Error('This step has changed. Refresh your routine and try again.');
      if (action === 'remove') steps = steps.filter((step) => step.product.id !== productId);
      else if (action === 'notes') steps[index] = { ...steps[index], notes: notes?.trim() || null };
      else {
        const other = action === 'up' ? index - 1 : index + 1;
        if (other >= 0 && other < steps.length)
          [steps[index], steps[other]] = [steps[other], steps[index]];
      }
      return request<Routine>(`/routines/${slot}`, {
        auth: true,
        method: 'PUT',
        body: { steps: routineInputs(steps) },
      });
    },
    onSuccess: () => {
      notifySuccess();
      setNotice('Routine updated.');
      void queryClient.invalidateQueries({ queryKey: privateKey('routines', uid) });
    },
  });
  const createShare = useMutation({
    mutationFn: () =>
      request<RoutineShare>(`/routines/${slot}/share`, {
        method: 'POST',
        auth: true,
        body: { expires_in_days: 7 },
      }),
    onSuccess: (link) => {
      notifySuccess();
      setNotice(t('routineShare.created'));
      void queryClient.invalidateQueries({
        queryKey: [...privateKey('routine-shares', uid), slot],
      });
      const url = Linking.createURL(sharedRoutinePath(link.share_token));
      void Share.share({ message: `${t('routineShare.publicTitle')}\n${url}`, url });
    },
  });
  const revokeShare = useMutation({
    mutationFn: (shareId: string) =>
      request(`/routines/shares/${encodeURIComponent(shareId)}`, {
        method: 'DELETE',
        auth: true,
      }),
    onSuccess: () => {
      notifySuccess();
      setNotice(t('routineShare.revoked'));
      void queryClient.invalidateQueries({
        queryKey: [...privateKey('routine-shares', uid), slot],
      });
    },
  });
  return (
    <ScreenList<RoutineStep>
      title="Your routines"
      data={uid ? (routine?.steps ?? []) : []}
      keyExtractor={(step) => `${step.product.id}-${step.notes ?? ''}`}
      renderItem={({ item: step, index }) => (
        <StepRow
          step={step}
          index={index}
          count={routine?.steps.length ?? 0}
          pending={mutation.isPending}
          onChange={(action, productId, notes) => {
            setNotice('');
            mutation.mutate({ action, productId, notes });
          }}
        />
      )}
      ListHeaderComponent={
        uid ? (
          <View style={{ gap: 22, paddingBottom: 22 }}>
            <AppText weight="semibold" style={{ fontSize: 28 }}>
              A little consistency.
            </AppText>
            <View style={{ flexDirection: 'row', gap: 10 }}>
              {(['morning', 'evening'] as const).map((value) => (
                <Button
                  key={value}
                  style={{ flex: 1 }}
                  isDisabled={mutation.isPending}
                  variant={slot === value ? 'primary' : 'secondary'}
                  onPress={() => {
                    setSlot(value);
                    setNotice('');
                    mutation.reset();
                    void Haptics.selectionAsync();
                  }}
                >
                  <Button.Label>{value === 'morning' ? 'Morning' : 'Evening'}</Button.Label>
                </Button>
              ))}
            </View>
          </View>
        ) : undefined
      }
      ListEmptyComponent={
        !uid ? (
          <SignInGate message="Sign in to build your morning and evening routines." />
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
            message="Your skincare steps will appear here."
            action="Add first step"
            onAction={() => router.push({ pathname: '/routine/add', params: { slot } })}
          />
        )
      }
      ListFooterComponent={
        uid ? (
          <View style={{ gap: 22, paddingTop: 18 }}>
            {!!routine?.steps.length && (
              <>
                <Conflicts conflicts={routine.conflicts} />
                <Button
                  variant={routine.completed_today ? 'secondary' : 'primary'}
                  isDisabled={mutation.isPending}
                  onPress={() => mutation.mutate({ action: 'complete' })}
                >
                  <Button.Label>
                    {mutation.isPending
                      ? 'Updating…'
                      : routine.completed_today
                        ? 'Undo today’s completion'
                        : 'Mark done today'}
                  </Button.Label>
                </Button>
              </>
            )}
            {!!routine?.steps.length && result.isError && (
              <DataState
                error={result.error}
                onAction={() => {
                  void result.refetch();
                }}
              />
            )}
            <Button
              isDisabled={mutation.isPending || result.isPending || result.isError}
              variant="secondary"
              onPress={() => router.push({ pathname: '/routine/add', params: { slot } })}
            >
              <Button.Label>Add a step</Button.Label>
            </Button>
            {mutation.isError && <FieldError>{errorMessage(mutation.error)}</FieldError>}
            {!!notice && <AppText style={{ color: colors.green }}>{notice}</AppText>}
            <Button variant="tertiary" onPress={() => router.push('/recommendations')}>
              <Button.Label>Find recommendations</Button.Label>
            </Button>
            {!!routine?.steps.length && (
              <View
                style={{
                  gap: 12,
                  borderTopWidth: 1,
                  borderTopColor: colors.border,
                  paddingTop: 18,
                }}
              >
                <Button
                  isDisabled={createShare.isPending || result.isPending}
                  variant="secondary"
                  style={{ minHeight: 48 }}
                  onPress={() => createShare.mutate()}
                >
                  <Button.Label>
                    {createShare.isPending ? t('routineShare.creating') : t('routineShare.share')}
                  </Button.Label>
                </Button>
                {createShare.isError && <FieldError>{errorMessage(createShare.error)}</FieldError>}
                {revokeShare.isError && <FieldError>{errorMessage(revokeShare.error)}</FieldError>}
                {shareLinks.isError ? (
                  <DataState
                    error={shareLinks.error}
                    onAction={() => {
                      void shareLinks.refetch();
                    }}
                  />
                ) : (
                  !!shareLinks.data?.links.length && (
                    <View style={{ gap: 8 }}>
                      <AppText weight="semibold">{t('routineShare.activeLinks')}</AppText>
                      {shareLinks.data.links.map((link) => (
                        <View
                          key={link.id}
                          style={{
                            flexDirection: 'row',
                            alignItems: 'center',
                            justifyContent: 'space-between',
                            gap: 8,
                            borderBottomWidth: 1,
                            borderBottomColor: colors.border,
                            paddingVertical: 8,
                          }}
                        >
                          <View style={{ flex: 1, gap: 4 }}>
                            <AppText style={{ color: colors.muted, fontSize: 12 }}>
                              {t('routineShare.expires', {
                                date: new Date(link.expires_at).toLocaleDateString(),
                              })}
                            </AppText>
                            <AppText style={{ color: colors.muted, fontSize: 12 }}>
                              {t('routineShare.views', { count: link.view_count })}
                            </AppText>
                          </View>
                          <Button
                            size="sm"
                            variant="tertiary"
                            isDisabled={revokeShare.isPending}
                            style={{ minHeight: 44 }}
                            onPress={() => revokeShare.mutate(link.id)}
                          >
                            <Button.Label>{t('routineShare.revoke')}</Button.Label>
                          </Button>
                        </View>
                      ))}
                    </View>
                  )
                )}
              </View>
            )}
          </View>
        ) : undefined
      }
    />
  );
}
