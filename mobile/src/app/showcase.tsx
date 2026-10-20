import type { ReactElement } from 'react';
import { useState } from 'react';
import { Redirect } from 'expo-router';
import { Switch, Text, View } from 'react-native';
import {
  EmptyState,
  ErrorState,
  ProductCard,
  RiskBadge,
  ScoreBadge,
  Screen,
  Skeleton,
} from '@/components';
import { useI18n } from '@/i18n';
import { useTheme } from '@/theme/theme';
export default function ShowcaseRoute(): ReactElement {
  const [gray, setGray] = useState(false);
  const { t } = useI18n();
  const { colors } = useTheme();
  if (!__DEV__) return <Redirect href="/" />;
  return (
    <Screen title={t('showcase')}>
      <View
        accessibilityRole="summary"
        style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}
      >
        <Text style={{ color: colors.text }}>{gray ? t('grayscale') : t('colorPreview')}</Text>
        <Switch value={gray} onValueChange={setGray} accessibilityLabel={t('toggleGrayscale')} />
      </View>
      <Text style={{ color: colors.text, fontSize: 20 }}>{t('concernIndicators')}</Text>
      {(['low', 'moderate', 'high', 'unknown'] as const).map((level) => (
        <RiskBadge key={level} level={level} grayscale={gray} />
      ))}
      <Text style={{ color: colors.text, fontSize: 20 }}>{t('scoreBands')}</Text>
      {(['low', 'moderate', 'high', 'unknown'] as const).map((band, i) => (
        <ScoreBadge
          key={band}
          score={band === 'unknown' ? null : [82, 61, 29][i]}
          band={band}
          grayscale={gray}
        />
      ))}
      <ProductCard
        name="Dew Veil Barrier Moisturizer with a deliberately long name"
        brand="Mora"
        category="Moisturizer"
        score={72}
        scoreBand="moderate"
        risk="high"
        onPress={() => undefined}
      />
      <ProductCard name="Product without a photo or brand" onPress={() => undefined} />
      <Skeleton variant="block" reduceMotion />
      <Skeleton variant="line" reduceMotion />
      <Skeleton variant="product" reduceMotion />
      <ErrorState onRetry={() => undefined} variant="offline" />
      <ErrorState onRetry={() => undefined} variant="server" />
      <EmptyState />
      <View style={{ flexDirection: 'row', gap: 8 }}>
        {Object.entries(colors)
          .filter(([key, value]) => typeof value === 'string')
          .map(([key, value]) => (
            <View
              key={key}
              style={{ backgroundColor: value as string, width: 44, height: 44, borderRadius: 10 }}
            />
          ))}
      </View>
      <Text style={{ fontSize: 13, color: colors.secondaryText }}>{t('sample')}</Text>
    </Screen>
  );
}
