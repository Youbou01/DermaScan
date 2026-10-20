import type { ReactElement } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { radii, spacing, typography, useThemeColors } from '@/theme/tokens';

export interface ErrorStateProps {
  title?: string;
  description?: string;
  onRetry?: () => void;
  buttonLabel?: string;
}

export function ErrorState({
  title = 'Something went wrong',
  description = 'We could not load this information. Please try again.',
  onRetry,
  buttonLabel = 'Try again',
}: ErrorStateProps): ReactElement {
  const colors = useThemeColors();
  return (
    <View style={styles.container}>
      <Text
        accessibilityElementsHidden
        style={[styles.icon, { color: colors.high, borderColor: colors.high }]}
      >
        !
      </Text>
      <Text accessibilityRole="header" style={[styles.title, { color: colors.text }]}>
        {title}
      </Text>
      <Text style={[styles.description, { color: colors.textMuted }]}>{description}</Text>
      {onRetry ? (
        <Pressable
          accessibilityRole="button"
          onPress={onRetry}
          style={({ pressed }) => [
            styles.button,
            { backgroundColor: colors.primary, opacity: pressed ? 0.75 : 1 },
          ]}
        >
          <Text style={[styles.buttonText, { color: colors.onPrimary }]}>{buttonLabel}</Text>
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
