import type { ReactNode } from 'react';
import { KeyboardAvoidingView, Platform, ScrollView } from 'react-native';
import { Link, router, Stack } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { colors } from '@/lib/theme';
export function ScreenHeader({ title }: { title: string }) {
  return (
    <Stack.Screen
      options={{
        title,
        headerLeft: router.canGoBack()
          ? undefined
          : () => (
              <Link
                href="/"
                style={{ color: colors.ink, padding: 12, fontFamily: 'Inter_500Medium' }}
              >
                Home
              </Link>
            ),
      }}
    />
  );
}
export function Screen({ title, children }: { title: string; children: ReactNode }) {
  const insets = useSafeAreaInsets();
  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      style={{ flex: 1, backgroundColor: colors.background }}
    >
      <ScreenHeader title={title} />
      <ScrollView
        keyboardShouldPersistTaps="handled"
        contentContainerStyle={{ padding: 22, gap: 22, paddingBottom: insets.bottom + 30 }}
      >
        {children}
      </ScrollView>
    </KeyboardAvoidingView>
  );
}
