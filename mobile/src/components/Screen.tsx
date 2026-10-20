import type { ReactElement, ReactNode } from 'react';
import { KeyboardAvoidingView, Platform, ScrollView, StyleSheet, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useThemeColors } from '@/theme/tokens';

export interface ScreenProps {
  children: ReactNode;
  scroll?: boolean;
  contentContainerStyle?: object;
}

export function Screen({
  children,
  scroll = true,
  contentContainerStyle,
}: ScreenProps): ReactElement {
  const colors = useThemeColors();
  return (
    <SafeAreaView
      edges={['top', 'right', 'bottom', 'left']}
      style={[styles.root, { backgroundColor: colors.background }]}
    >
      {scroll ? (
        <KeyboardAvoidingView
          behavior={Platform.OS === 'ios' ? 'padding' : undefined}
          style={styles.root}
        >
          <ScrollView
            contentContainerStyle={[styles.content, contentContainerStyle]}
            keyboardShouldPersistTaps="handled"
          >
            {children}
          </ScrollView>
        </KeyboardAvoidingView>
      ) : (
        <View style={styles.root}>{children}</View>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({ root: { flex: 1 }, content: { flexGrow: 1 } });
