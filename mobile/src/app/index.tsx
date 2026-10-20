import type { ReactElement } from 'react';
import { useTranslation } from 'react-i18next';
import { StyleSheet, Text, View } from 'react-native';

import { LanguageSwitch } from '@/components/LanguageSwitch';

// Placeholder until MOB-06 (Home). The language switch moves to a settings screen later.
export default function HomeRoute(): ReactElement {
  const { t } = useTranslation();

  return (
    <View style={styles.container}>
      <Text accessibilityRole="header" style={styles.title}>
        {t('home.title')}
      </Text>
      <LanguageSwitch />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: 24 },
  title: { fontSize: 28, fontWeight: '600' },
});
