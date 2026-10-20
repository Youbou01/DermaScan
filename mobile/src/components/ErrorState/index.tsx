import type { ReactElement } from 'react';
import { Pressable, Text, View } from 'react-native';
import { useI18n } from '@/i18n';
import { useTheme } from '@/theme/theme';
export interface ErrorStateProps {
  readonly variant?: 'generic' | 'offline' | 'server';
  readonly error?: unknown;
  readonly onRetry: () => void;
}
export function ErrorState({
  variant = 'generic',
  error: _error,
  onRetry,
}: ErrorStateProps): ReactElement {
  const { t } = useI18n();
  const { colors, radius } = useTheme();
  const title =
    variant === 'offline'
      ? t('offlineTitle')
      : variant === 'server'
        ? t('serverTitle')
        : t('errorTitle');
  const message =
    variant === 'offline'
      ? t('offlineMessage')
      : variant === 'server'
        ? t('serverMessage')
        : t('errorMessage');
  return (
    <View accessibilityLiveRegion="polite" style={{ alignItems: 'center', gap: 12, padding: 24 }}>
      <Text accessible={false} style={{ fontSize: 28 }}>
        !
      </Text>
      <Text
        accessibilityRole="header"
        style={{ color: colors.text, fontSize: 20, fontWeight: '700' }}
      >
        {title}
      </Text>
      <Text style={{ color: colors.secondaryText, fontSize: 16, textAlign: 'center' }}>
        {message}
      </Text>
      <Pressable
        accessibilityRole="button"
        onPress={onRetry}
        style={{
          minHeight: 48,
          justifyContent: 'center',
          paddingHorizontal: 18,
          borderRadius: radius.md,
          backgroundColor: colors.primary,
        }}
      >
        <Text style={{ color: colors.inverseText, fontSize: 16, fontWeight: '700' }}>
          {t('retry')}
        </Text>
      </Pressable>
    </View>
  );
}
