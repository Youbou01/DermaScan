import { useState, type ReactElement } from 'react';
import { Pressable, StyleSheet, Text, TextInput, View } from 'react-native';
import { useRouter, type Href } from 'expo-router';
import { useProfileQuery, useUpdateProfileMutation } from '@/api/hooks';
import type { ProfileDTO } from '@/api/contracts';
import { productCardsFixture } from '@/api/fixtures';
import { EmptyState, ErrorState, Screen, Skeleton } from '@/components';
import { useTranslation } from '@/i18n/useTranslation';
import { spacing, typography, useThemeColors } from '@/theme/tokens';
import { useAuth } from '@/features/auth/AuthProvider';

const skinTypes = ['normal', 'dry', 'oily', 'combination', 'sensitive'] as const;
const conditions = ['eczema', 'rosacea', 'acne_prone'] as const;
const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export function ProfileScreen(): ReactElement {
  const { user, isReady, signOut } = useAuth();
  const router = useRouter();
  const { t } = useTranslation();
  const colors = useThemeColors();
  const query = useProfileQuery(user?.id);
  const update = useUpdateProfileMutation(user?.id);
  const [allergyId, setAllergyId] = useState('');
  const [allergyError, setAllergyError] = useState('');

  if (!isReady || query.isPending)
    return (
      <Screen>
        <Skeleton height={52} />
        <Skeleton height={100} />
        <Skeleton height={160} />
      </Screen>
    );
  if (!user)
    return (
      <Screen>
        <EmptyState
          title={t('auth.sign_in')}
          description={t('profile.sign_in_required')}
          action={
            <Pressable
              accessibilityRole="button"
              onPress={() => router.push('/auth/sign-in' as unknown as Href)}
              style={[styles.button, { backgroundColor: colors.primary }]}
            >
              <Text style={{ color: colors.onPrimary }}>{t('auth.sign_in')}</Text>
            </Pressable>
          }
        />
      </Screen>
    );
  if (query.isError && !query.data)
    return (
      <Screen>
        <ErrorState onRetry={() => void query.refetch()} description={t('profile.unavailable')} />
      </Screen>
    );
  const profile = query.data;
  if (!profile)
    return (
      <Screen>
        <EmptyState title={t('profile.title')} description={t('errors.generic_description')} />
      </Screen>
    );

  function save(patch: Partial<ProfileDTO>): void {
    update.mutate({ ...profile, ...patch });
  }
  function toggleCondition(condition: (typeof conditions)[number]): void {
    const next = profile.health_conditions.includes(condition)
      ? profile.health_conditions.filter((item) => item !== condition)
      : [...profile.health_conditions, condition];
    save({ health_conditions: next });
  }
  function addAllergy(): void {
    const id = allergyId.trim();
    if (!uuidPattern.test(id)) {
      setAllergyError(t('profile.invalid_id'));
      return;
    }
    setAllergyError('');
    if (!profile.allergy_ingredient_ids.includes(id))
      save({ allergy_ingredient_ids: [...profile.allergy_ingredient_ids, id] });
    setAllergyId('');
  }
  function removeBlacklisted(id: string): void {
    save({
      blacklisted_product_ids: profile.blacklisted_product_ids.filter((item) => item !== id),
    });
  }

  return (
    <Screen contentContainerStyle={styles.content}>
      <Text accessibilityRole="header" style={[styles.heading, { color: colors.text }]}>
        {t('profile.title')}
      </Text>
      <Text accessibilityRole="header" style={[styles.section, { color: colors.text }]}>
        {t('profile.skin_type')}
      </Text>
      <View style={styles.wrap}>
        {skinTypes.map((skin) => (
          <Pressable
            key={skin}
            accessibilityRole="radio"
            accessibilityState={{ selected: profile.skin_type === skin }}
            onPress={() => save({ skin_type: skin })}
            style={[
              styles.choice,
              {
                backgroundColor: profile.skin_type === skin ? colors.primary : colors.surface,
                borderColor: colors.border,
              },
            ]}
          >
            <Text style={{ color: profile.skin_type === skin ? colors.onPrimary : colors.text }}>
              {t(`profile.${skin}`)}
            </Text>
          </Pressable>
        ))}
      </View>
      <Text accessibilityRole="header" style={[styles.section, { color: colors.text }]}>
        {t('profile.health')}
      </Text>
      <Toggle
        label={t('profile.pregnant')}
        value={profile.is_pregnant_or_nursing}
        onToggle={(value) => save({ is_pregnant_or_nursing: value })}
      />
      {conditions.map((condition) => (
        <Toggle
          key={condition}
          label={t(`profile.${condition}`)}
          value={profile.health_conditions.includes(condition)}
          onToggle={() => toggleCondition(condition)}
        />
      ))}
      <Text accessibilityRole="header" style={[styles.section, { color: colors.text }]}>
        {t('profile.allergies')}
      </Text>
      <View style={styles.row}>
        <TextInput
          accessibilityLabel={t('profile.allergy_placeholder')}
          placeholder={t('profile.allergy_placeholder')}
          value={allergyId}
          onChangeText={setAllergyId}
          onSubmitEditing={addAllergy}
          style={[
            styles.input,
            { backgroundColor: colors.surface, color: colors.text, borderColor: colors.border },
          ]}
        />
        <Pressable
          accessibilityRole="button"
          onPress={addAllergy}
          style={[styles.button, { backgroundColor: colors.primary }]}
        >
          <Text style={{ color: colors.onPrimary }}>{t('profile.add_allergy')}</Text>
        </Pressable>
      </View>
      {allergyError ? (
        <Text accessibilityRole="alert" style={{ color: colors.high }}>
          {allergyError}
        </Text>
      ) : null}
      {profile.allergy_ingredient_ids.map((id) => (
        <Toggle
          key={id}
          label={id}
          value
          onToggle={() =>
            save({
              allergy_ingredient_ids: profile.allergy_ingredient_ids.filter((item) => item !== id),
            })
          }
        />
      ))}
      <Text accessibilityRole="header" style={[styles.section, { color: colors.text }]}>
        {t('profile.blacklist')}
      </Text>
      {profile.blacklisted_product_ids.some(
        (id) => !productCardsFixture.some((product) => product.id === id),
      ) ? (
        <Text style={{ color: colors.textMuted }}>{t('profile.blacklist_unavailable')}</Text>
      ) : null}
      {profile.blacklisted_product_ids.length === 0 ? (
        <Text style={{ color: colors.textMuted }}>{t('profile.blacklist_empty')}</Text>
      ) : (
        profile.blacklisted_product_ids.map((id) => {
          const product = productCardsFixture.find((item) => item.id === id);
          const name = product?.name ?? id;
          return (
            <View
              key={id}
              style={[
                styles.blacklistRow,
                { backgroundColor: colors.surface, borderColor: colors.border },
              ]}
            >
              <Text style={[styles.blacklistName, { color: colors.text }]}>{name}</Text>
              <Pressable
                accessibilityRole="button"
                accessibilityLabel={t('profile.remove', { name })}
                onPress={() => removeBlacklisted(id)}
                style={[styles.removeButton, { borderColor: colors.border }]}
              >
                <Text style={{ color: colors.text }}>{t('profile.remove', { name })}</Text>
              </Pressable>
            </View>
          );
        })
      )}
      {update.isError ? (
        <Text accessibilityRole="alert" style={{ color: colors.high }}>
          {t('profile.unavailable')}
        </Text>
      ) : null}
      {update.isPending ? (
        <Text accessibilityRole="text" style={{ color: colors.textMuted }}>
          {t('profile.saving')}
        </Text>
      ) : null}
      <Pressable
        accessibilityRole="button"
        onPress={() => void signOut()}
        style={[styles.signOut, { borderColor: colors.border }]}
      >
        <Text style={{ color: colors.text }}>{t('auth.sign_out')}</Text>
      </Pressable>
    </Screen>
  );
}

interface ToggleProps {
  label: string;
  value: boolean;
  onToggle: (value: boolean) => void;
}
function Toggle({ label, value, onToggle }: ToggleProps): ReactElement {
  const colors = useThemeColors();
  return (
    <Pressable
      accessibilityRole="switch"
      accessibilityLabel={label}
      accessibilityState={{ checked: value }}
      onPress={() => onToggle(!value)}
      style={[styles.toggle, { backgroundColor: colors.surface, borderColor: colors.border }]}
    >
      <Text style={{ color: colors.text }}>{label}</Text>
      <Text accessibilityElementsHidden style={{ color: colors.primary }}>
        {value ? '✓' : '○'}
      </Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  content: { gap: spacing.md, padding: spacing.lg, paddingBottom: spacing.xxxl },
  heading: {
    fontSize: typography.size.xl,
    lineHeight: typography.lineHeight.xl,
    fontWeight: typography.weight.bold,
  },
  section: {
    marginTop: spacing.md,
    fontSize: typography.size.lg,
    lineHeight: typography.lineHeight.lg,
    fontWeight: typography.weight.semibold,
  },
  wrap: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm },
  choice: {
    minHeight: 48,
    justifyContent: 'center',
    paddingHorizontal: spacing.md,
    borderWidth: 1,
    borderRadius: 12,
  },
  toggle: {
    minHeight: 48,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: spacing.md,
    borderWidth: 1,
    borderRadius: 12,
  },
  row: { flexDirection: 'row', gap: spacing.sm, alignItems: 'center' },
  input: {
    minHeight: 44,
    flex: 1,
    borderWidth: 1,
    borderRadius: 10,
    paddingHorizontal: spacing.md,
  },
  button: {
    minHeight: 44,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: spacing.md,
    borderRadius: 10,
  },
  blacklistRow: {
    minHeight: 56,
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    padding: spacing.sm,
    borderWidth: 1,
    borderRadius: 12,
  },
  blacklistName: { flex: 1, fontSize: typography.size.md },
  removeButton: {
    minHeight: 44,
    justifyContent: 'center',
    paddingHorizontal: spacing.md,
    borderWidth: 1,
    borderRadius: 10,
  },
  signOut: {
    minHeight: 48,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderRadius: 12,
  },
});
