import type { ReactElement } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { useProfileQuery, useUpdateProfileMutation } from '@/api/hooks';
import { useAuth } from '@/features/auth/AuthProvider';
import { RiskBadge } from '@/components';
import { useTranslation } from '@/i18n/useTranslation';
import { spacing, typography, useThemeColors } from '@/theme/tokens';

interface BlacklistButtonProps {
  productId: string;
}

export function BlacklistButton({ productId }: BlacklistButtonProps): ReactElement | null {
  const { user, isAuthenticated } = useAuth();
  const { t } = useTranslation();
  const colors = useThemeColors();
  const query = useProfileQuery(user?.id);
  const update = useUpdateProfileMutation(user?.id);
  if (!isAuthenticated || !user) return null;
  const profile = query.data;
  const isBlacklisted = profile?.blacklisted_product_ids.includes(productId) ?? false;
  function toggle(): void {
    if (!profile) return;
    const ids = isBlacklisted
      ? profile.blacklisted_product_ids.filter((id) => id !== productId)
      : [...profile.blacklisted_product_ids, productId];
    update.mutate({ ...profile, blacklisted_product_ids: ids });
  }
  return (
    <View style={styles.container}>
      {isBlacklisted ? (
        <View
          accessibilityRole="alert"
          style={[
            styles.warning,
            { backgroundColor: colors.highSurface, borderColor: colors.high },
          ]}
        >
          <RiskBadge level="high" />
          <Text style={[styles.warningText, { color: colors.text }]}>
            {t('suitability.blacklisted')}
          </Text>
        </View>
      ) : null}
      <Pressable
        accessibilityRole="button"
        accessibilityState={{ disabled: !profile || update.isPending }}
        accessibilityLabel={t(
          isBlacklisted ? 'suitability.remove_blacklist' : 'suitability.add_blacklist',
        )}
        disabled={!profile || update.isPending}
        onPress={toggle}
        style={[
          styles.button,
          {
            backgroundColor: isBlacklisted ? colors.surface : colors.primary,
            borderColor: colors.primary,
            opacity: !profile || update.isPending ? 0.6 : 1,
          },
        ]}
      >
        <Text style={{ color: isBlacklisted ? colors.primary : colors.onPrimary }}>
          {t(isBlacklisted ? 'suitability.remove_blacklist' : 'suitability.add_blacklist')}
        </Text>
      </Pressable>
      {query.isError || update.isError ? (
        <Text accessibilityRole="alert" style={{ color: colors.high }}>
          {t('suitability.unavailable')}
        </Text>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { gap: spacing.sm },
  warning: { gap: spacing.sm, padding: spacing.md, borderWidth: 2, borderRadius: 12 },
  warningText: {
    fontSize: typography.size.md,
    lineHeight: typography.lineHeight.md,
    fontWeight: typography.weight.semibold,
  },
  button: {
    minHeight: 48,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderRadius: 12,
    paddingHorizontal: spacing.md,
  },
});
