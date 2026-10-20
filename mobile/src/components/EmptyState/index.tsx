import type { ReactElement } from 'react';
import { Text, View } from 'react-native';
import { useI18n } from '@/i18n';
import { useTheme } from '@/theme/theme';
export interface EmptyStateProps {
  readonly title?: string;
  readonly message?: string;
  readonly actionLabel?: string;
  readonly onAction?: () => void;
}
export function EmptyState({
  title,
  message,
  actionLabel,
  onAction,
}: EmptyStateProps): ReactElement {
  const { t } = useI18n();
  const { colors } = useTheme();
  return (
    <View style={{ alignItems: 'center', gap: 12, padding: 24 }}>
      <Text accessible={false} style={{ fontSize: 28 }}>
        ◇
      </Text>
      <Text
        accessibilityRole="header"
        style={{ color: colors.text, fontSize: 20, fontWeight: '700', textAlign: 'center' }}
      >
        {title ?? t('emptyTitle')}
      </Text>
      <Text style={{ color: colors.secondaryText, fontSize: 16, textAlign: 'center' }}>
        {message ?? t('emptyMessage')}
      </Text>
      {actionLabel && onAction ? (
        <Text
          accessibilityRole="button"
          accessibilityLabel={actionLabel}
          onPress={onAction}
          style={{ color: colors.primary, minHeight: 44, padding: 12, fontWeight: '700' }}
        >
          {actionLabel}
        </Text>
      ) : null}
    </View>
  );
}
