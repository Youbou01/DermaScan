import type { ReactElement } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import type { RiskLevel } from '@/api/types';
import { radii, spacing, typography, useThemeColors } from '@/theme/tokens';

const labels: Record<RiskLevel, string> = {
  low: 'Low concern',
  moderate: 'Moderate concern',
  high: 'High concern',
  unknown: 'Insufficient data',
};
const icons: Record<RiskLevel, string> = { low: '○', moderate: '△', high: '⬟', unknown: '◇' };
const colorKeys: Record<RiskLevel, 'low' | 'moderate' | 'high' | 'unknown'> = {
  low: 'low',
  moderate: 'moderate',
  high: 'high',
  unknown: 'unknown',
};

export interface RiskBadgeProps {
  level: RiskLevel;
  grayscale?: boolean;
}

export function RiskBadge({ level, grayscale = false }: RiskBadgeProps): ReactElement {
  const colors = useThemeColors();
  const color = grayscale ? colors.text : colors[colorKeys[level]];
  return (
    <View
      accessibilityRole="text"
      accessibilityLabel={`Risk level: ${labels[level]}`}
      style={[
        styles.badge,
        {
          backgroundColor: grayscale ? colors.surfaceMuted : colors[`${colorKeys[level]}Surface`],
          borderColor: color,
        },
      ]}
    >
      <Text accessibilityLabel={`Risk icon: ${icons[level]}`} style={[styles.icon, { color }]}>
        {icons[level]}
      </Text>
      <Text style={[styles.label, { color }]}>{labels[level]}</Text>
    </View>
  );
}

export const riskBadgeMeta = { labels, icons };

const styles = StyleSheet.create({
  badge: {
    minHeight: 32,
    flexDirection: 'row',
    alignItems: 'center',
    alignSelf: 'flex-start',
    gap: spacing.xs,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.xs,
    borderWidth: 1,
    borderRadius: radii.pill,
  },
  icon: { fontSize: typography.size.md, fontWeight: typography.weight.bold },
  label: {
    fontSize: typography.size.sm,
    lineHeight: typography.lineHeight.sm,
    fontWeight: typography.weight.semibold,
  },
});
