import type { ReactElement } from 'react';
import { Text, View } from 'react-native';
import { useI18n } from '@/i18n';
import { useTheme } from '@/theme/theme';
export type ScoreBand = 'low' | 'moderate' | 'high' | 'unknown';
export interface ScoreBadgeProps {
  readonly score?: number | null;
  readonly band?: ScoreBand;
  readonly loading?: boolean;
  readonly grayscale?: boolean;
}
export function ScoreBadge({
  score,
  band = 'unknown',
  loading = false,
  grayscale = false,
}: ScoreBadgeProps): ReactElement {
  const { t } = useI18n();
  const { colors } = useTheme();
  const key =
    band === 'low'
      ? 'favorable'
      : band === 'moderate'
        ? 'caution'
        : band === 'high'
          ? 'flagged'
          : 'unknown';
  const label = t(key);
  const token = colors[key];
  const noScore = score === null || score === undefined || band === 'unknown';
  const msg = loading ? t('loading') : noScore ? t('unknown') : t('score', { score, band: label });
  return (
    <View
      accessible
      accessibilityRole="text"
      accessibilityLabel={msg}
      style={{
        minWidth: 56,
        minHeight: 44,
        alignItems: 'center',
        justifyContent: 'center',
        paddingHorizontal: 10,
        borderRadius: 14,
        backgroundColor: grayscale ? '#FFFFFF' : token.background,
        borderWidth: 1,
        borderColor: grayscale ? '#222222' : token.border,
      }}
    >
      <Text
        accessible={false}
        style={{ color: grayscale ? '#111111' : token.foreground, fontSize: 18, fontWeight: '700' }}
      >
        {loading ? '…' : noScore ? '?' : score}
      </Text>
      <Text
        accessible={false}
        style={{ color: grayscale ? '#111111' : token.foreground, fontSize: 12 }}
      >
        {label}
      </Text>
    </View>
  );
}
