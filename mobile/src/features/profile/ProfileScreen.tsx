import { useRouter, type Href } from 'expo-router';
import { useState, type ReactElement } from 'react';
import { Pressable, StyleSheet, Switch, Text, View } from 'react-native';
import { KNOWN_PROFILE_INGREDIENTS } from '@/api/fixtures';
import type { BlacklistOut, HealthCondition, ProfileOut, SkinType } from '@/api/types';
import { Screen, Skeleton } from '@/components';
import { env } from '@/config/env';
import { useAuth } from '@/features/auth/AuthContext';
import { useLanguage } from '@/i18n/LanguageProvider';
import { useTranslation } from '@/i18n/useTranslation';
import { radii, spacing, typography, useThemeColors } from '@/theme/tokens';
import {
  ProfileAuthRequiredError,
  useBlacklistedProductsDetails,
  useBlacklistQuery,
  useProfileQuery,
  useToggleBlacklistIngredientMutation,
  useToggleBlacklistProductMutation,
  useUpdateProfileMutation,
} from './profile-api';

const SKIN_TYPES: readonly SkinType[] = ['normal', 'dry', 'oily', 'combination', 'sensitive'];
const HEALTH_CONDITIONS: readonly HealthCondition[] = [
  'eczema',
  'rosacea',
  'acne_prone',
  'psoriasis',
];

interface ProfileScreenContentProps {
  readonly initialProfile: ProfileOut;
  readonly blacklist?: BlacklistOut;
}

function ProfileScreenContent({
  initialProfile,
  blacklist,
}: ProfileScreenContentProps): ReactElement {
  const router = useRouter();
  const colors = useThemeColors();
  const { t } = useTranslation();
  const { currentLanguage, setLanguage } = useLanguage();
  const { user, isAuthenticated, signOut } = useAuth();

  const updateProfile = useUpdateProfileMutation();
  const toggleBlacklistIngredient = useToggleBlacklistIngredientMutation();
  const toggleBlacklistProduct = useToggleBlacklistProductMutation();

  const [skinType, setSkinType] = useState<SkinType | null>(initialProfile.skin_type);
  const [isPregnant, setIsPregnant] = useState(initialProfile.is_pregnant_or_nursing);
  const [conditions, setConditions] = useState<HealthCondition[]>(initialProfile.health_conditions);
  const [allergies, setAllergies] = useState<string[]>(initialProfile.allergy_ingredient_ids);
  const [savedNotice, setSavedNotice] = useState(false);

  const [prevProfile, setPrevProfile] = useState(initialProfile);
  if (prevProfile !== initialProfile) {
    setPrevProfile(initialProfile);
    if (!isAuthenticated && !env.useMocks) {
      setSkinType(null);
      setIsPregnant(false);
      setConditions([]);
      setAllergies([]);
      setSavedNotice(false);
    } else {
      setSkinType(initialProfile.skin_type);
      setIsPregnant(initialProfile.is_pregnant_or_nursing);
      setConditions(initialProfile.health_conditions);
      setAllergies(initialProfile.allergy_ingredient_ids);
    }
  }

  const blacklistedIngredientIds = blacklist?.ingredient_ids ?? [];
  const blacklistedProductIds = blacklist?.product_ids ?? [];
  const productDetailsMap = useBlacklistedProductsDetails(blacklistedProductIds);

  const toggleCondition = (cond: HealthCondition): void => {
    setSavedNotice(false);
    setConditions((prev) =>
      prev.includes(cond) ? prev.filter((item) => item !== cond) : [...prev, cond],
    );
  };

  const toggleAllergy = (ingredientId: string): void => {
    setSavedNotice(false);
    setAllergies((prev) =>
      prev.includes(ingredientId)
        ? prev.filter((id) => id !== ingredientId)
        : [...prev, ingredientId],
    );
  };

  const handleSaveProfile = async (): Promise<void> => {
    if (!env.useMocks && !isAuthenticated) {
      router.push('/auth/login' as unknown as Href);
      return;
    }
    try {
      await updateProfile.mutateAsync({
        skin_type: skinType,
        is_pregnant_or_nursing: isPregnant,
        health_conditions: conditions,
        allergy_ingredient_ids: allergies,
      });
      setSavedNotice(true);
    } catch (err) {
      if (err instanceof ProfileAuthRequiredError) {
        await signOut();
        router.push('/auth/login' as unknown as Href);
      }
    }
  };

  const handleToggleIngredientBlacklist = async (ingredientId: string): Promise<void> => {
    if (!env.useMocks && !isAuthenticated) {
      router.push('/auth/login' as unknown as Href);
      return;
    }
    try {
      await toggleBlacklistIngredient.mutateAsync(ingredientId);
    } catch (err) {
      if (err instanceof ProfileAuthRequiredError) {
        await signOut();
        router.push('/auth/login' as unknown as Href);
      }
    }
  };

  const handleToggleProductBlacklist = async (productId: string): Promise<void> => {
    if (!env.useMocks && !isAuthenticated) {
      router.push('/auth/login' as unknown as Href);
      return;
    }
    try {
      await toggleBlacklistProduct.mutateAsync(productId);
    } catch (err) {
      if (err instanceof ProfileAuthRequiredError) {
        await signOut();
        router.push('/auth/login' as unknown as Href);
      }
    }
  };

  return (
    <Screen contentContainerStyle={styles.content}>
      <Pressable
        accessibilityRole="button"
        accessibilityLabel={t('auth.back_home')}
        onPress={() => router.push('/' as unknown as Href)}
        style={[styles.backButton, { borderColor: colors.border }]}
      >
        <Text style={[styles.backText, { color: colors.primary }]}>‹ {t('auth.back_home')}</Text>
      </Pressable>

      <Text accessibilityRole="header" style={[styles.title, { color: colors.text }]}>
        {t('profile.title')}
      </Text>
      <Text style={[styles.subtitle, { color: colors.textMuted }]}>{t('profile.subtitle')}</Text>

      <View
        style={[
          styles.sectionCard,
          { backgroundColor: colors.surface, borderColor: colors.border },
        ]}
      >
        <Text accessibilityRole="header" style={[styles.sectionTitle, { color: colors.text }]}>
          {t('profile.account_heading')}
        </Text>
        <View style={styles.rowWrap}>
          {(['en', 'fr'] as const).map((lang) => {
            const selected = currentLanguage === lang;
            const label = lang === 'en' ? t('common.english') : t('common.french');
            return (
              <Pressable
                key={lang}
                accessibilityRole="button"
                accessibilityLabel={label}
                accessibilityState={{ selected }}
                onPress={() => {
                  void setLanguage(lang);
                }}
                style={[
                  styles.pill,
                  {
                    backgroundColor: selected ? colors.primary : colors.background,
                    borderColor: selected ? colors.primary : colors.border,
                  },
                ]}
              >
                <Text
                  style={[styles.pillText, { color: selected ? colors.onPrimary : colors.text }]}
                >
                  {label}
                </Text>
              </Pressable>
            );
          })}
        </View>
        {isAuthenticated && user ? (
          <View style={styles.authRow}>
            <Text style={[styles.signedInText, { color: colors.text }]}>
              {t('auth.signed_in_as', { name: user.display_name })}
            </Text>
            <Pressable
              accessibilityRole="button"
              accessibilityLabel={t('auth.sign_out')}
              onPress={() => {
                void signOut();
              }}
              style={[styles.outlineButton, { borderColor: colors.high }]}
            >
              <Text style={[styles.outlineButtonText, { color: colors.high }]}>
                {t('auth.sign_out')}
              </Text>
            </Pressable>
          </View>
        ) : (
          <Pressable
            accessibilityRole="button"
            accessibilityLabel={t('profile.sign_in_prompt')}
            onPress={() => router.push('/auth/login' as unknown as Href)}
            style={[styles.outlineButton, { borderColor: colors.primary }]}
          >
            <Text style={[styles.outlineButtonText, { color: colors.primary }]}>
              {t('profile.sign_in_prompt')}
            </Text>
          </Pressable>
        )}
      </View>

      <View
        style={[
          styles.sectionCard,
          { backgroundColor: colors.surface, borderColor: colors.border },
        ]}
      >
        <Text accessibilityRole="header" style={[styles.sectionTitle, { color: colors.text }]}>
          {t('profile.skin_type_heading')}
        </Text>
        <View style={styles.rowWrap}>
          {SKIN_TYPES.map((option) => {
            const selected = skinType === option;
            const label = t(`profile.skin_types.${option}`);
            return (
              <Pressable
                key={option}
                accessibilityRole="button"
                accessibilityLabel={label}
                accessibilityState={{ selected }}
                onPress={() => {
                  setSavedNotice(false);
                  setSkinType(selected ? null : option);
                }}
                style={[
                  styles.pill,
                  {
                    backgroundColor: selected ? colors.primary : colors.background,
                    borderColor: selected ? colors.primary : colors.border,
                  },
                ]}
              >
                <Text
                  style={[styles.pillText, { color: selected ? colors.onPrimary : colors.text }]}
                >
                  {label}
                </Text>
              </Pressable>
            );
          })}
        </View>

        <View style={styles.switchRow}>
          <View style={styles.switchTextCol}>
            <Text style={[styles.switchLabel, { color: colors.text }]}>
              {t('profile.pregnancy_label')}
            </Text>
            <Text style={[styles.switchHint, { color: colors.textMuted }]}>
              {t('profile.pregnancy_hint')}
            </Text>
          </View>
          <Switch
            accessibilityLabel={t('profile.pregnancy_label')}
            onValueChange={(val) => {
              setSavedNotice(false);
              setIsPregnant(val);
            }}
            value={isPregnant}
          />
        </View>

        <Text accessibilityRole="header" style={[styles.sectionTitle, { color: colors.text }]}>
          {t('profile.conditions_heading')}
        </Text>
        <View style={styles.rowWrap}>
          {HEALTH_CONDITIONS.map((cond) => {
            const selected = conditions.includes(cond);
            const label = t(`profile.conditions.${cond}`);
            return (
              <Pressable
                key={cond}
                accessibilityRole="button"
                accessibilityLabel={label}
                accessibilityState={{ selected }}
                onPress={() => toggleCondition(cond)}
                style={[
                  styles.pill,
                  {
                    backgroundColor: selected ? colors.primary : colors.background,
                    borderColor: selected ? colors.primary : colors.border,
                  },
                ]}
              >
                <Text
                  style={[styles.pillText, { color: selected ? colors.onPrimary : colors.text }]}
                >
                  {label}
                </Text>
              </Pressable>
            );
          })}
        </View>

        <Text accessibilityRole="header" style={[styles.sectionTitle, { color: colors.text }]}>
          {t('profile.allergies_heading')}
        </Text>
        <View style={styles.rowWrap}>
          {KNOWN_PROFILE_INGREDIENTS.map((ing) => {
            const selected = allergies.includes(ing.id);
            const label = currentLanguage === 'fr' ? ing.label_fr : ing.label_en;
            return (
              <Pressable
                key={`allergy-${ing.id}`}
                accessibilityRole="button"
                accessibilityLabel={`Allergy: ${label}`}
                accessibilityState={{ selected }}
                onPress={() => toggleAllergy(ing.id)}
                style={[
                  styles.pill,
                  {
                    backgroundColor: selected ? colors.moderateSurface : colors.background,
                    borderColor: selected ? colors.moderate : colors.border,
                  },
                ]}
              >
                <Text
                  style={[styles.pillText, { color: selected ? colors.moderate : colors.text }]}
                >
                  {selected ? '✓ ' : ''}
                  {label}
                </Text>
              </Pressable>
            );
          })}
        </View>

        {savedNotice ? (
          <Text
            accessibilityLiveRegion="polite"
            style={[styles.savedBanner, { color: colors.primary }]}
          >
            {t('profile.saved_confirmation')}
          </Text>
        ) : null}

        <Pressable
          accessibilityRole="button"
          accessibilityLabel={t('profile.save_button')}
          disabled={updateProfile.isPending}
          onPress={() => {
            void handleSaveProfile();
          }}
          style={({ pressed }) => [
            styles.saveButton,
            {
              backgroundColor: colors.primary,
              opacity: pressed || updateProfile.isPending ? 0.75 : 1,
            },
          ]}
        >
          <Text style={[styles.saveButtonText, { color: colors.onPrimary }]}>
            {t('profile.save_button')}
          </Text>
        </Pressable>
      </View>

      <View
        style={[
          styles.sectionCard,
          { backgroundColor: colors.surface, borderColor: colors.border },
        ]}
      >
        <Text accessibilityRole="header" style={[styles.sectionTitle, { color: colors.text }]}>
          {t('profile.blacklist_ingredients_heading')}
        </Text>
        <View style={styles.rowWrap}>
          {KNOWN_PROFILE_INGREDIENTS.map((ing) => {
            const isBlacklisted = blacklistedIngredientIds.includes(ing.id);
            const label = currentLanguage === 'fr' ? ing.label_fr : ing.label_en;
            return (
              <Pressable
                key={`bl-${ing.id}`}
                accessibilityRole="button"
                accessibilityLabel={`Blacklist: ${label}`}
                accessibilityState={{ selected: isBlacklisted }}
                disabled={toggleBlacklistIngredient.isPending}
                onPress={() => {
                  void handleToggleIngredientBlacklist(ing.id);
                }}
                style={[
                  styles.pill,
                  {
                    backgroundColor: isBlacklisted ? colors.highSurface : colors.background,
                    borderColor: isBlacklisted ? colors.high : colors.border,
                  },
                ]}
              >
                <Text
                  style={[styles.pillText, { color: isBlacklisted ? colors.high : colors.text }]}
                >
                  {isBlacklisted ? '⬟ ' : '+ '}
                  {label}
                </Text>
              </Pressable>
            );
          })}
        </View>

        <Text accessibilityRole="header" style={[styles.sectionTitle, { color: colors.text }]}>
          {t('profile.blacklist_products_heading')}
        </Text>
        {blacklistedProductIds.length === 0 ? (
          <Text style={[styles.emptyText, { color: colors.textMuted }]}>
            {t('profile.empty_blacklist_products')}
          </Text>
        ) : (
          <View style={styles.productList}>
            {blacklistedProductIds.map((pid) => {
              const resolved = productDetailsMap[pid];
              const displayName = resolved
                ? resolved.brand
                  ? `${resolved.name} (${resolved.brand})`
                  : resolved.name
                : pid;
              return (
                <View key={pid} style={[styles.productRow, { borderColor: colors.border }]}>
                  <Pressable
                    accessibilityRole="button"
                    accessibilityLabel={displayName}
                    onPress={() =>
                      router.push({
                        pathname: '/products/[productId]',
                        params: { productId: pid },
                      } as unknown as Href)
                    }
                    style={styles.productNameButton}
                  >
                    <Text style={[styles.productName, { color: colors.text }]}>{displayName}</Text>
                  </Pressable>
                  <Pressable
                    accessibilityRole="button"
                    accessibilityLabel={t('profile.remove_product', { id: displayName })}
                    disabled={toggleBlacklistProduct.isPending}
                    onPress={() => {
                      void handleToggleProductBlacklist(pid);
                    }}
                    style={[styles.removeButton, { borderColor: colors.high }]}
                  >
                    <Text style={{ color: colors.high }}>×</Text>
                  </Pressable>
                </View>
              );
            })}
          </View>
        )}
      </View>
    </Screen>
  );
}

export function ProfileScreen(): ReactElement {
  const profileQuery = useProfileQuery();
  const blacklistQuery = useBlacklistQuery();

  if (profileQuery.isPending || blacklistQuery.isPending || !profileQuery.data) {
    return (
      <Screen contentContainerStyle={styles.content}>
        <Skeleton height={48} />
        <Skeleton height={120} />
        <Skeleton height={120} />
      </Screen>
    );
  }

  return (
    <ProfileScreenContent
      key={profileQuery.data.user_id}
      initialProfile={profileQuery.data}
      blacklist={blacklistQuery.data}
    />
  );
}

const styles = StyleSheet.create({
  content: { padding: spacing.lg, gap: spacing.md, paddingBottom: spacing.xxxl },
  backButton: {
    minHeight: 44,
    alignSelf: 'flex-start',
    justifyContent: 'center',
    paddingHorizontal: spacing.md,
    borderWidth: 1,
    borderRadius: radii.md,
  },
  backText: {
    fontSize: typography.size.sm,
    fontWeight: typography.weight.semibold,
  },
  title: {
    fontSize: typography.size.xl,
    lineHeight: typography.lineHeight.xl,
    fontWeight: typography.weight.bold,
  },
  subtitle: {
    fontSize: typography.size.sm,
    lineHeight: typography.lineHeight.sm,
  },
  sectionCard: {
    gap: spacing.md,
    padding: spacing.lg,
    borderWidth: 1,
    borderRadius: radii.lg,
  },
  sectionTitle: {
    fontSize: typography.size.md,
    fontWeight: typography.weight.bold,
  },
  rowWrap: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.sm,
  },
  pill: {
    minHeight: 44,
    justifyContent: 'center',
    paddingHorizontal: spacing.md,
    borderWidth: 1,
    borderRadius: radii.pill,
  },
  pillText: {
    fontSize: typography.size.sm,
    fontWeight: typography.weight.semibold,
  },
  switchRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: spacing.md,
  },
  switchTextCol: {
    flex: 1,
    gap: 2,
  },
  switchLabel: {
    fontSize: typography.size.md,
    fontWeight: typography.weight.semibold,
  },
  switchHint: {
    fontSize: typography.size.xs,
  },
  authRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: spacing.sm,
  },
  signedInText: {
    fontSize: typography.size.sm,
    fontWeight: typography.weight.medium,
  },
  outlineButton: {
    minHeight: 44,
    alignSelf: 'flex-start',
    justifyContent: 'center',
    paddingHorizontal: spacing.md,
    borderWidth: 1,
    borderRadius: radii.md,
  },
  outlineButtonText: {
    fontSize: typography.size.sm,
    fontWeight: typography.weight.semibold,
  },
  savedBanner: {
    fontSize: typography.size.sm,
    fontWeight: typography.weight.semibold,
  },
  saveButton: {
    minHeight: 48,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: radii.md,
    paddingHorizontal: spacing.lg,
  },
  saveButtonText: {
    fontSize: typography.size.md,
    fontWeight: typography.weight.semibold,
  },
  emptyText: {
    fontSize: typography.size.sm,
  },
  productList: {
    gap: spacing.sm,
  },
  productRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: spacing.sm,
    padding: spacing.sm,
    borderWidth: 1,
    borderRadius: radii.md,
  },
  productNameButton: {
    flex: 1,
    minHeight: 44,
    justifyContent: 'center',
  },
  productName: {
    fontSize: typography.size.sm,
    fontWeight: typography.weight.medium,
  },
  removeButton: {
    minWidth: 44,
    minHeight: 44,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderRadius: radii.sm,
  },
});
