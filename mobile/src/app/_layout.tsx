import { Stack } from 'expo-router';
import type { ReactElement } from 'react';
import { I18nextProvider } from 'react-i18next';

import { i18n } from '@/i18n';

/**
 * Root layout. Providers (query client, theme) are added here by MOB-01 and MOB-02.
 * Routes in this folder stay thin: they render a screen from `src/features/*`.
 */
export default function RootLayout(): ReactElement {
  return (
    <I18nextProvider i18n={i18n}>
      <Stack screenOptions={{ headerShown: false }} />
    </I18nextProvider>
  );
}
