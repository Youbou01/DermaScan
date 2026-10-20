import type { ReactElement, ReactNode } from 'react';
import {
  KeyboardAvoidingView,
  Platform,
  RefreshControl,
  ScrollView,
  Text,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useTheme } from '@/theme/theme';
export interface ScreenProps {
  readonly children: ReactNode;
  readonly title?: string;
  readonly scroll?: boolean;
  readonly keyboardAvoiding?: boolean;
  readonly refreshing?: boolean;
  readonly onRefresh?: () => void;
}
export function Screen({
  children,
  title,
  scroll = true,
  keyboardAvoiding = false,
  refreshing = false,
  onRefresh,
}: ScreenProps): ReactElement {
  const { colors, spacing } = useTheme();
  const content = scroll ? (
    <ScrollView
      contentContainerStyle={{ padding: spacing.md, gap: spacing.md, flexGrow: 1 }}
      keyboardShouldPersistTaps="handled"
      refreshControl={
        onRefresh ? <RefreshControl refreshing={refreshing} onRefresh={onRefresh} /> : undefined
      }
    >
      {title ? (
        <Text
          accessibilityRole="header"
          style={{ color: colors.text, fontSize: 24, fontWeight: '700' }}
        >
          {title}
        </Text>
      ) : null}
      {children}
    </ScrollView>
  ) : (
    <View style={{ flex: 1, padding: spacing.md }}>
      {title ? (
        <Text
          accessibilityRole="header"
          style={{ color: colors.text, fontSize: 24, fontWeight: '700' }}
        >
          {title}
        </Text>
      ) : null}
      {children}
    </View>
  );
  const body = keyboardAvoiding ? (
    <KeyboardAvoidingView
      style={{ flex: 1 }}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      {content}
    </KeyboardAvoidingView>
  ) : (
    content
  );
  return (
    <SafeAreaView
      style={{ flex: 1, backgroundColor: colors.background }}
      edges={['top', 'left', 'right']}
    >
      {body}
    </SafeAreaView>
  );
}
