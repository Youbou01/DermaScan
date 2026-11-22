import { useState } from 'react';
import { View } from 'react-native';
import { Button, ControlField, Label, FieldError } from 'heroui-native';
import { useMutation } from '@tanstack/react-query';
import { router } from 'expo-router';
import * as Haptics from 'expo-haptics';
import { Screen } from '@/components/Screen';
import { AppText } from '@/components/AppText';
import { DataState, LoadingState, SignInGate } from '@/components/DataState';
import { notifySuccess, privateKey, queryClient, useProfile, useUserId } from '@/lib/api/queries';
import { errorMessage, request } from '@/lib/api/client';
import {
  conditions,
  skinTypes,
  type HealthCondition,
  type Profile,
  type ProfileInput,
} from '@/lib/api/types';
import { colors } from '@/lib/theme';
const labels: Record<HealthCondition, string> = {
  eczema: 'Eczema',
  rosacea: 'Rosacea',
  acne_prone: 'Acne-prone',
  psoriasis: 'Psoriasis',
};
function ProfileForm({ profile }: { profile: Profile }) {
  const [form, setForm] = useState<ProfileInput>({
    skin_type: profile.skin_type,
    is_pregnant_or_nursing: profile.is_pregnant_or_nursing,
    health_conditions: profile.health_conditions,
    allergy_ingredient_ids: profile.allergy_ingredient_ids,
  });
  const [saved, setSaved] = useState(false);
  const uid = useUserId();
  const mutation = useMutation({
    mutationFn: async () => {
      const current = await request<Profile>('/profile', { auth: true });
      return request<Profile>('/profile', {
        method: 'PUT',
        auth: true,
        body: { ...form, allergy_ingredient_ids: current.allergy_ingredient_ids },
      });
    },
    onSuccess: (result) => {
      queryClient.setQueryData(privateKey('profile', uid), result);
      void queryClient.invalidateQueries({ queryKey: ['suitability'] });
      void queryClient.invalidateQueries({ queryKey: ['recommendations'] });
      setSaved(true);
      notifySuccess();
    },
  });
  function update(next: Partial<ProfileInput>) {
    setForm({ ...form, ...next });
    setSaved(false);
    void Haptics.selectionAsync();
  }
  return (
    <>
      <AppText weight="semibold" style={{ fontSize: 28 }}>
        Your skin, your choices.
      </AppText>
      <View style={{ gap: 12 }}>
        <Label>Skin type</Label>
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8 }}>
          {skinTypes.map((value) => (
            <Button
              key={value}
              size="sm"
              variant={form.skin_type === value ? 'primary' : 'secondary'}
              onPress={() => update({ skin_type: form.skin_type === value ? null : value })}
            >
              <Button.Label>{value.charAt(0).toUpperCase() + value.slice(1)}</Button.Label>
            </Button>
          ))}
        </View>
      </View>
      <ControlField
        isSelected={form.is_pregnant_or_nursing}
        onSelectedChange={(value) => update({ is_pregnant_or_nursing: value })}
      >
        <Label style={{ flex: 1 }}>Pregnant or nursing</Label>
        <ControlField.Indicator />
      </ControlField>
      <View style={{ gap: 12 }}>
        <Label>Skin conditions</Label>
        {conditions.map((condition) => (
          <ControlField
            key={condition}
            isSelected={form.health_conditions.includes(condition)}
            onSelectedChange={(selected) =>
              update({
                health_conditions: selected
                  ? [...form.health_conditions, condition]
                  : form.health_conditions.filter((value) => value !== condition),
              })
            }
          >
            <Label style={{ flex: 1 }}>{labels[condition]}</Label>
            <ControlField.Indicator />
          </ControlField>
        ))}
      </View>
      <View style={{ gap: 10 }}>
        <AppText weight="medium">
          {profile.allergy_ingredient_ids.length} saved{' '}
          {profile.allergy_ingredient_ids.length === 1 ? 'allergy' : 'allergies'}
        </AppText>
        <AppText style={{ color: colors.muted, fontSize: 12, lineHeight: 19 }}>
          Add or remove allergies from an ingredient&apos;s explanation on a product page.
        </AppText>
        <Button variant="tertiary" onPress={() => router.push('/')}>
          <Button.Label>Find a product</Button.Label>
        </Button>
      </View>
      <Button variant="secondary" onPress={() => router.push('/avoidance')}>
        <Button.Label>Products you avoid</Button.Label>
      </Button>
      {mutation.isError && <FieldError>{errorMessage(mutation.error)}</FieldError>}
      {saved && <AppText style={{ color: colors.green }}>Profile saved.</AppText>}
      <Button isDisabled={mutation.isPending} onPress={() => mutation.mutate()}>
        <Button.Label>{mutation.isPending ? 'Saving…' : 'Save profile'}</Button.Label>
      </Button>
    </>
  );
}
export default function ProfileScreen() {
  const uid = useUserId();
  const result = useProfile();
  return (
    <Screen title="Skin profile">
      {!uid ? (
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
        result.data && <ProfileForm key={uid} profile={result.data} />
      )}
    </Screen>
  );
}
