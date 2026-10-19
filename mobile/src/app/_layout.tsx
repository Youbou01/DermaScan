import { Stack } from 'expo-router';
import type { ReactElement } from 'react';

/**
 * Root layout. Providers (query client, i18n, theme) are added here by MOB-01 to MOB-03.
 * Routes in this folder stay thin: they render a screen from `src/features/*`.
 */
export default function RootLayout(): ReactElement {
  return <Stack screenOptions={{ headerShown: false }} />;
}
