import type { ReactElement } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import type { RiskLevel } from '@/api/types';
import { radii, spacing, typography, useThemeColors } from '@/theme/tokens';

export interface ScoreBadgeProps {
  score: number | null;
  band?: RiskLevel | null;
}

export function ScoreBadge({ score, band }: ScoreBadgeProps): ReactElement {
  const colors = useThemeColors();
  const tier =
    band ?? (score === null ? 'unknown' : score >= 75 ? 'low' : score >= 40 ? 'moderate' : 'high');
  const label = score === null || tier === 'unknown' ? 'Insufficient data' : `${score} / 100`;
  const fg = colors[tier];
  return (
    <View
      accessibilityRole="text"
      accessibilityLabel={
        score === null || tier === 'unknown'
          ? 'Score: insufficient data'
          : `Score: ${score} out of 100`
      }
      style={[styles.badge, { backgroundColor: colors[`${tier}Surface`], borderColor: fg }]}
    >
      <Text style={[styles.text, { color: fg }]}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    minHeight: 32,
    justifyContent: 'center',
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.xs,
    borderWidth: 1,
    borderRadius: radii.pill,
  },
  text: {
    fontSize: typography.size.sm,
    lineHeight: typography.lineHeight.sm,
    fontWeight: typography.weight.bold,
  },
});
