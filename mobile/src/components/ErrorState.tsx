import type { ReactElement } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { radii, spacing, typography, useThemeColors } from '@/theme/tokens';
import { useTranslation } from '@/i18n/useTranslation';

export interface ErrorStateProps {
  title?: string;
  description?: string;
  onRetry?: () => void;
  buttonLabel?: string;
}

export function ErrorState({
  title,
  description,
  onRetry,
  buttonLabel,
}: ErrorStateProps): ReactElement {
  const { t } = useTranslation();
  const colors = useThemeColors();
  const displayedTitle = title ?? t('errors.generic_title');
  const displayedDescription = description ?? t('errors.generic_description');
  return (
    <View style={styles.container}>
      <Text
        accessibilityElementsHidden
        style={[styles.icon, { color: colors.high, borderColor: colors.high }]}
      >
        !
      </Text>
      <Text accessibilityRole="header" style={[styles.title, { color: colors.text }]}>
        {displayedTitle}
      </Text>
      <Text style={[styles.description, { color: colors.textMuted }]}>{displayedDescription}</Text>
      {onRetry ? (
        <Pressable
          accessibilityRole="button"
          onPress={onRetry}
          style={({ pressed }) => [
            styles.button,
            { backgroundColor: colors.primary, opacity: pressed ? 0.75 : 1 },
          ]}
        >
          <Text style={[styles.buttonText, { color: colors.onPrimary }]}>
            {buttonLabel ?? t('common.retry')}
          </Text>
        </Pressable>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    minHeight: 220,
    alignItems: 'center',
    justifyContent: 'center',
    padding: spacing.xl,
    gap: spacing.md,
  },
  icon: {
    width: 48,
    height: 48,
    borderWidth: 2,
    borderRadius: radii.pill,
    textAlign: 'center',
    textAlignVertical: 'center',
    fontSize: typography.size.xl,
    fontWeight: typography.weight.bold,
  },
  title: {
    textAlign: 'center',
    fontSize: typography.size.lg,
    lineHeight: typography.lineHeight.lg,
    fontWeight: typography.weight.bold,
  },
  description: {
    maxWidth: 320,
    textAlign: 'center',
    fontSize: typography.size.md,
    lineHeight: typography.lineHeight.md,
  },
  button: {
    minWidth: 120,
    minHeight: 44,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: spacing.xl,
    borderRadius: radii.md,
  },
  buttonText: { fontSize: typography.size.md, fontWeight: typography.weight.semibold },
});
