import { Stack } from 'expo-router';
import type { ReactElement } from 'react';
import { QueryClientProvider } from '@tanstack/react-query';
import { queryClient } from '@/api/query-client';
import { AuthProvider } from '@/features/auth/AuthContext';
import { LanguageProvider } from '@/i18n/LanguageProvider';

export default function RootLayout(): ReactElement {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <LanguageProvider>
          <Stack screenOptions={{ headerShown: false }} />
        </LanguageProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}
