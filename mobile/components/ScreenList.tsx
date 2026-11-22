import { FlatList, KeyboardAvoidingView, Platform, type FlatListProps } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { ScreenHeader } from './Screen';
import { colors } from '@/lib/theme';
export function ScreenList<T>({
  title,
  contentContainerStyle,
  ...props
}: FlatListProps<T> & { title: string }) {
  const insets = useSafeAreaInsets();
  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      style={{ flex: 1, backgroundColor: colors.background }}
    >
      <ScreenHeader title={title} />
      <FlatList
        {...props}
        keyboardShouldPersistTaps="handled"
        contentContainerStyle={[
          { padding: 22, paddingBottom: insets.bottom + 30 },
          contentContainerStyle,
        ]}
      />
    </KeyboardAvoidingView>
  );
}
