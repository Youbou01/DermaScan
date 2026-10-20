import { Stack } from 'expo-router';
import type { ReactElement } from 'react';
import { QueryClientProvider } from '@tanstack/react-query';
import { queryClient } from '@/api/query-client';
import { LanguageProvider } from '@/i18n/LanguageProvider';

/**
 * Root layout providers are shared by every route.
 * Routes in this folder stay thin: they render a screen from `src/features/*`.
 */
export default function RootLayout(): ReactElement {
  return (
    <QueryClientProvider client={queryClient}>
      <LanguageProvider>
        <Stack screenOptions={{ headerShown: false }} />
      </LanguageProvider>
    </QueryClientProvider>
  );
}
