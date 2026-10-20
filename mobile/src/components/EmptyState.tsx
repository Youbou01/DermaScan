import type { ReactElement, ReactNode } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { spacing, typography, useThemeColors } from '@/theme/tokens';

export interface EmptyStateProps {
  title: string;
  description: string;
  icon?: string;
  action?: ReactNode;
}

export function EmptyState({
  title,
  description,
  icon = '○',
  action,
}: EmptyStateProps): ReactElement {
  const colors = useThemeColors();
  return (
    <View style={styles.container}>
      <Text accessibilityElementsHidden style={[styles.icon, { color: colors.primary }]}>
        {icon}
      </Text>
      <Text accessibilityRole="header" style={[styles.title, { color: colors.text }]}>
        {title}
      </Text>
      <Text style={[styles.description, { color: colors.textMuted }]}>{description}</Text>
      {action}
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
  icon: { fontSize: 48 },
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
});
