import type { ReactElement } from 'react';
import { useState } from 'react';
import { Image, Pressable, Text, View } from 'react-native';
import { useI18n } from '@/i18n';
import { ScoreBadge } from '@/components/ScoreBadge';
import { RiskBadge, type RiskLevel } from '@/components/RiskBadge';
import { useTheme } from '@/theme/theme';
export interface ProductCardProps {
  readonly name: string;
  readonly brand?: string | null;
  readonly category?: string;
  readonly score?: number | null;
  readonly scoreBand?: RiskLevel;
  readonly risk?: RiskLevel;
  readonly imageUrl?: string | null;
  readonly onPress: () => void;
}
function riskKey(level: RiskLevel): 'favorable' | 'caution' | 'flagged' | 'unknown' {
  return level === 'low'
    ? 'favorable'
    : level === 'moderate'
      ? 'caution'
      : level === 'high'
        ? 'flagged'
        : 'unknown';
}
export function ProductCard({
  name,
  brand,
  category,
  score,
  scoreBand = 'unknown',
  risk,
  imageUrl,
  onPress,
}: ProductCardProps): ReactElement {
  const { t } = useI18n();
  const { colors, radius } = useTheme();
  const [imageFailed, setImageFailed] = useState(false);
  const label = [
    name,
    brand,
    score === null || score === undefined
      ? t('unknown')
      : t('score', { score, band: t(riskKey(scoreBand)) }),
    risk ? t(riskKey(risk)) : '',
  ]
    .filter(Boolean)
    .join(', ');
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={label}
      onPress={onPress}
      style={({ pressed }) => ({
        minHeight: 96,
        flexDirection: 'row',
        alignItems: 'center',
        gap: 14,
        padding: 16,
        backgroundColor: colors.surface,
        borderColor: colors.border,
        borderWidth: 1,
        borderRadius: radius.md,
        opacity: pressed ? 0.75 : 1,
      })}
    >
      <View
        accessible={false}
        style={{
          width: 64,
          height: 64,
          borderRadius: radius.sm,
          backgroundColor: colors.background,
          alignItems: 'center',
          justifyContent: 'center',
          overflow: 'hidden',
        }}
      >
        {imageUrl && !imageFailed ? (
          <Image
            source={{ uri: imageUrl }}
            resizeMode="cover"
            onError={() => setImageFailed(true)}
            style={{ width: 64, height: 64 }}
          />
        ) : (
          <Text style={{ color: colors.secondaryText }}>◇</Text>
        )}
      </View>
      <View style={{ flex: 1, gap: 4 }}>
        <Text numberOfLines={2} style={{ color: colors.text, fontSize: 16, fontWeight: '700' }}>
          {name}
        </Text>
        <Text numberOfLines={1} style={{ color: colors.secondaryText }}>
          {brand || t('unknown')}
        </Text>
        {category ? (
          <Text style={{ color: colors.secondaryText, fontSize: 13 }}>{category}</Text>
        ) : null}
      </View>
      <View accessible={false} style={{ gap: 4 }}>
        <ScoreBadge score={score} band={scoreBand} />
        {risk ? <RiskBadge level={risk} size="small" /> : null}
      </View>
    </Pressable>
  );
}
