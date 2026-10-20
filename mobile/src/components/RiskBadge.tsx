import type { ReactElement } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import type { RiskLevel } from '@/api/types';
import { radii, spacing, typography, useThemeColors } from '@/theme/tokens';
import { useTranslation } from '@/i18n/useTranslation';

const labelKeys: Record<RiskLevel, `risk.${RiskLevel}`> = {
  low: 'risk.low',
  moderate: 'risk.moderate',
  high: 'risk.high',
  unknown: 'risk.unknown',
};
const accessibilityKeys: Record<RiskLevel, `risk.accessibility.${RiskLevel}`> = {
  low: 'risk.accessibility.low',
  moderate: 'risk.accessibility.moderate',
  high: 'risk.accessibility.high',
  unknown: 'risk.accessibility.unknown',
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
  const { t } = useTranslation();
  const colors = useThemeColors();
  const color = grayscale ? colors.text : colors[colorKeys[level]];
  const label = t(labelKeys[level]);
  return (
    <View
      accessibilityRole="text"
      accessibilityLabel={t(accessibilityKeys[level])}
      style={[
        styles.badge,
        {
          backgroundColor: grayscale ? colors.surfaceMuted : colors[`${colorKeys[level]}Surface`],
          borderColor: color,
        },
      ]}
    >
      <Text
        accessibilityElementsHidden
        importantForAccessibility="no"
        style={[styles.icon, { color }]}
      >
        {icons[level]}
      </Text>
      <Text style={[styles.label, { color }]}>{label}</Text>
    </View>
  );
}

export const riskBadgeMeta = { labelKeys, icons };

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
