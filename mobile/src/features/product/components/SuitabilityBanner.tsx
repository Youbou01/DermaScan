import type { ReactElement } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { useProductSuitabilityQuery } from '@/api/hooks';
import { useAuth } from '@/features/auth/AuthProvider';
import { RiskBadge } from '@/components';
import { useTranslation } from '@/i18n/useTranslation';
import { spacing, typography, useThemeColors } from '@/theme/tokens';

interface SuitabilityBannerProps {
  productId: string;
}

export function SuitabilityBanner({ productId }: SuitabilityBannerProps): ReactElement | null {
  const { user, isAuthenticated } = useAuth();
  const { t } = useTranslation();
  const colors = useThemeColors();
  const query = useProductSuitabilityQuery(productId, user?.id);
  if (!isAuthenticated) return null;
  if (query.isPending)
    return (
      <View accessibilityRole="text" style={[styles.card, { borderColor: colors.border }]}>
        <Text style={{ color: colors.textMuted }}>{t('common.loading')}</Text>
      </View>
    );
  if (query.isError || !query.data)
    return (
      <View accessibilityRole="alert" style={[styles.card, { borderColor: colors.moderate }]}>
        <RiskBadge level="unknown" />
        <Text style={{ color: colors.text }}>{t('suitability.unavailable')}</Text>
      </View>
    );
  const suitability = query.data;
  const level =
    suitability.verdict === 'avoid'
      ? 'high'
      : suitability.verdict === 'caution'
        ? 'moderate'
        : 'low';
  const alerts = suitability.alerts.filter((alert) => alert.code !== 'blacklisted');
  return (
    <View
      accessibilityRole={suitability.has_risk_alert ? 'alert' : 'summary'}
      style={[
        styles.card,
        {
          backgroundColor: colors.surface,
          borderColor: suitability.has_risk_alert ? colors[level] : colors.border,
        },
      ]}
    >
      <RiskBadge level={level} />
      <Text accessibilityRole="header" style={[styles.heading, { color: colors.text }]}>
        {t(`suitability.${suitability.verdict}`)}
      </Text>
      {alerts.length ? (
        alerts.map((alert, index) => (
          <View key={`${alert.code}-${index}`} style={styles.alert}>
            <Text style={[styles.alertTitle, { color: colors.text }]}>{alert.title}</Text>
            <Text style={[styles.detail, { color: colors.textMuted }]}>{alert.detail}</Text>
          </View>
        ))
      ) : suitability.is_blacklisted ? null : (
        <Text style={[styles.detail, { color: colors.textMuted }]}>
          {t('suitability.no_reasons')}
        </Text>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  card: { gap: spacing.sm, padding: spacing.md, borderWidth: 1, borderRadius: 12 },
  heading: {
    fontSize: typography.size.md,
    lineHeight: typography.lineHeight.md,
    fontWeight: typography.weight.semibold,
  },
  alert: { gap: spacing.xs },
  alertTitle: {
    fontSize: typography.size.sm,
    lineHeight: typography.lineHeight.sm,
    fontWeight: typography.weight.semibold,
  },
  detail: { fontSize: typography.size.sm, lineHeight: typography.lineHeight.sm },
});
