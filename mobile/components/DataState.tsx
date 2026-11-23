import { View } from 'react-native';
import { Button, Skeleton } from 'heroui-native';
import { Search, AlertCircle, LogIn } from 'lucide-react-native';
import { router } from 'expo-router';
import { AppText } from './AppText';
import { colors } from '@/lib/theme';
import { errorMessage } from '@/lib/api/client';
export function LoadingState() {
  return (
    <View accessibilityLabel="Loading" style={{ gap: 16, paddingVertical: 14 }}>
      <Skeleton className="h-40 w-full rounded-2xl" style={{ backgroundColor: colors.border }} />
      <Skeleton className="h-6 w-3/4 rounded-lg" style={{ backgroundColor: colors.border }} />
      <Skeleton className="h-6 w-1/2 rounded-lg" style={{ backgroundColor: colors.border }} />
    </View>
  );
}
export function DataState({
  error,
  message,
  action = 'Try again',
  onAction,
}: {
  error?: unknown;
  message?: string;
  action?: string;
  onAction: () => void;
}) {
  const Icon = error ? AlertCircle : Search;
  return (
    <View style={{ alignItems: 'center', gap: 16, paddingVertical: 30, paddingHorizontal: 10 }}>
      <Icon size={30} color={error ? colors.red : colors.muted} strokeWidth={1.8} />
      <AppText style={{ textAlign: 'center', lineHeight: 22 }}>
        {message ?? errorMessage(error)}
      </AppText>
      <Button variant="secondary" onPress={onAction}>
        <Button.Label>{action}</Button.Label>
      </Button>
    </View>
  );
}
export function SignInGate({
  message = 'Sign in to make skincare personal.',
}: {
  message?: string;
}) {
  return (
    <View style={{ alignItems: 'center', gap: 18, paddingVertical: 32 }}>
      <LogIn size={34} color={colors.ink} strokeWidth={1.8} />
      <AppText style={{ textAlign: 'center' }}>{message}</AppText>
      <Button onPress={() => router.push('/account')}>
        <Button.Label>Sign in</Button.Label>
      </Button>
    </View>
  );
}
