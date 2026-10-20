import type { ReactElement } from 'react';
import { Text, View } from 'react-native';
import { useI18n } from '@/i18n';
import { useTheme, type RiskTokens } from '@/theme/theme';
export type RiskLevel = 'low' | 'moderate' | 'high' | 'unknown';
export interface RiskBadgeProps {
  readonly level: RiskLevel;
  readonly size?: 'small' | 'medium';
  readonly compact?: boolean;
  readonly grayscale?: boolean;
}
export function RiskBadge({
  level,
  size = 'medium',
  compact = false,
  grayscale = false,
}: RiskBadgeProps): ReactElement {
  const { t } = useI18n();
  const { colors } = useTheme();
  const map: Record<
    RiskLevel,
    { tokens: RiskTokens; key: 'favorable' | 'caution' | 'flagged' | 'unknown' }
  > = {
    low: { tokens: colors.favorable, key: 'favorable' },
    moderate: { tokens: colors.caution, key: 'caution' },
    high: { tokens: colors.flagged, key: 'flagged' },
    unknown: { tokens: colors.unknown, key: 'unknown' },
  };
  const item = map[level];
  const label = t(item.key);
  const color = grayscale ? '#FFFFFF' : item.tokens.background;
  const fg = grayscale ? '#111111' : item.tokens.foreground;
  return (
    <View
      accessible
      accessibilityRole="text"
      accessibilityLabel={`${label}`}
      style={{
        flexDirection: 'row',
        alignItems: 'center',
        alignSelf: 'flex-start',
        gap: 5,
        minHeight: 44,
        paddingHorizontal: 10,
        borderRadius: 999,
        backgroundColor: color,
        borderWidth: 1,
        borderColor: grayscale ? '#222222' : item.tokens.border,
      }}
    >
      <Text
        accessible={false}
        style={{ color: fg, fontSize: size === 'small' ? 13 : 16, fontWeight: '700' }}
      >
        {item.tokens.icon}
      </Text>
      {!compact && (
        <Text
          accessible={false}
          style={{
            color: fg,
            fontSize: size === 'small' ? 13 : 14,
            fontWeight: '600',
            flexShrink: 1,
          }}
        >
          {label}
        </Text>
      )}
    </View>
  );
}
