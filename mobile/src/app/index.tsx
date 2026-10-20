import type { ReactElement } from 'react';
import { Link } from 'expo-router';
import { Text, View } from 'react-native';
import { Screen } from '@/components';
import { useI18n } from '@/i18n';
import { useTheme } from '@/theme/theme';
export default function HomeRoute(): ReactElement {
  const { t } = useI18n();
  const { colors } = useTheme();
  return (
    <Screen>
      <View style={{ flex: 1, justifyContent: 'center', gap: 20 }}>
        <Text
          accessibilityRole="header"
          style={{ color: colors.text, fontSize: 28, fontWeight: '700' }}
        >
          {t('home')}
        </Text>
        {__DEV__ ? (
          <Link href="/showcase" style={{ color: colors.primary, fontSize: 18, minHeight: 44 }}>
            {t('showcase')} →
          </Link>
        ) : null}
      </View>
    </Screen>
  );
}
