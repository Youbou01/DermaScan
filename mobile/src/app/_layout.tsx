import { Stack } from 'expo-router';
import type { ReactElement } from 'react';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { ThemeProvider } from '@/theme/theme';
import { I18nProvider } from '@/i18n';
export default function RootLayout(): ReactElement {
  return (
    <SafeAreaProvider>
      <ThemeProvider>
        <I18nProvider>
          <Stack screenOptions={{ headerShown: false }} />
        </I18nProvider>
      </ThemeProvider>
    </SafeAreaProvider>
  );
}
