import { View } from 'react-native';
import { colors } from '@/lib/theme';
import { AppText } from '@/components/AppText';
import type { RiskBand } from '@/lib/api/types';
export const ratingColors: Record<RiskBand, { foreground: string; background: string }> = {
  low: { foreground: colors.green, background: colors.greenSoft },
  moderate: { foreground: colors.orange, background: colors.orangeSoft },
  high: { foreground: colors.red, background: colors.redSoft },
  unknown: { foreground: colors.muted, background: colors.border },
};
export const bandLabels: Record<RiskBand, string> = {
  low: 'Low concern',
  moderate: 'Moderate',
  high: 'High concern',
  unknown: 'Not rated',
};
export function ScoreBadge({ score, band }: { score: number | null; band: RiskBand | null }) {
  const palette = ratingColors[score === null ? 'unknown' : (band ?? 'unknown')];
  return (
    <View
      style={{
        flexDirection: 'row',
        alignItems: 'center',
        gap: 5,
        backgroundColor: palette.background,
        paddingHorizontal: 9,
        paddingVertical: 5,
        borderRadius: 20,
      }}
    >
      <View style={{ width: 5, height: 5, borderRadius: 3, backgroundColor: palette.foreground }} />
      <AppText
        weight="semibold"
        numberOfLines={1}
        style={{ fontSize: 11, color: palette.foreground }}
      >
        {score === null ? 'Not scored' : `${score}/100`}
      </AppText>
    </View>
  );
}
