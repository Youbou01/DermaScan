import type { ReactElement } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { useTranslation } from '@/i18n/useTranslation';
import { radii, spacing, typography, useThemeColors } from '@/theme/tokens';
import type { RoutineConflict } from '../routine-api';

export interface ConflictWarningBannerProps {
  readonly conflicts: readonly RoutineConflict[];
  readonly onPressDetails: () => void;
}

export function ConflictWarningBanner({
  conflicts,
  onPressDetails,
}: ConflictWarningBannerProps): ReactElement | null {
  const colors = useThemeColors();
  const { t } = useTranslation();

  if (conflicts.length === 0) {
    return null;
  }

  const hasHigh = conflicts.some((c) => c.severity === 'high');
  const fg = hasHigh ? colors.high : colors.moderate;
  const bg = hasHigh ? colors.highSurface : colors.moderateSurface;
  const title =
    conflicts.length === 1
      ? t('conflicts.banner_title_one')
      : t('conflicts.banner_title_other', { count: conflicts.length });

  return (
    <View
      accessibilityRole="alert"
      testID="conflict-warning-banner"
      style={[styles.banner, { backgroundColor: bg, borderColor: fg }]}
    >
      <View style={styles.headerRow}>
        <Text accessibilityElementsHidden style={[styles.icon, { color: fg }]}>
          {hasHigh ? '⬟' : '△'}
        </Text>
        <Text style={[styles.title, { color: fg }]}>{title}</Text>
      </View>
      <Text style={[styles.preview, { color: colors.text }]}>
        {conflicts[0]?.title}: {conflicts[0]?.product_a_name} + {conflicts[0]?.product_b_name}
      </Text>
      <Pressable
        accessibilityRole="button"
        accessibilityLabel={t('conflicts.banner_cta')}
        onPress={onPressDetails}
        style={({ pressed }) => [styles.button, { borderColor: fg, opacity: pressed ? 0.75 : 1 }]}
      >
        <Text style={[styles.buttonText, { color: fg }]}>{t('conflicts.banner_cta')}</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  banner: {
    gap: spacing.sm,
    padding: spacing.md,
    borderWidth: 1,
    borderRadius: radii.md,
  },
  headerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.xs,
  },
  icon: {
    fontSize: typography.size.lg,
    fontWeight: typography.weight.bold,
  },
  title: {
    flex: 1,
    fontSize: typography.size.md,
    lineHeight: typography.lineHeight.md,
    fontWeight: typography.weight.bold,
  },
  preview: {
    fontSize: typography.size.sm,
    lineHeight: typography.lineHeight.sm,
  },
  button: {
    minHeight: 44,
    alignSelf: 'flex-start',
    justifyContent: 'center',
    paddingHorizontal: spacing.md,
    borderWidth: 1,
    borderRadius: radii.md,
  },
  buttonText: {
    fontSize: typography.size.sm,
    fontWeight: typography.weight.semibold,
  },
});
