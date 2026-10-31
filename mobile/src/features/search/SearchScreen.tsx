import { useRouter, type Href } from 'expo-router';
import { useCallback, useEffect, useState, type ReactElement } from 'react';
import { Pressable, StyleSheet, Text, TextInput, View } from 'react-native';
import { Screen } from '@/components';
import { useTranslation } from '@/i18n/useTranslation';
import { radii, spacing, typography, useThemeColors } from '@/theme/tokens';
import { addRecentSearch, loadRecentSearches } from './recent-searches';
import { useDebouncedValue } from './useDebouncedValue';

const MIN_QUERY_LENGTH = 2;

export function SearchScreen(): ReactElement {
  const router = useRouter();
  const colors = useThemeColors();
  const { t } = useTranslation();
  const [text, setText] = useState('');
  const [tooShort, setTooShort] = useState(false);
  const [recent, setRecent] = useState<string[]>([]);
  const debouncedLength = useDebouncedValue(text.trim()).length;
  const showHint = tooShort || debouncedLength === 1;

  useEffect(() => {
    let active = true;
    void loadRecentSearches().then((items) => {
      if (active) setRecent(items);
    });
    return () => {
      active = false;
    };
  }, []);

  const submit = useCallback(
    async (value: string): Promise<void> => {
      const term = value.trim();
      if (term.length < MIN_QUERY_LENGTH) {
        setTooShort(true);
        return;
      }
      setTooShort(false);
      setRecent(await addRecentSearch(term));
      router.push({ pathname: '/products', params: { q: term } } as unknown as Href);
    },
    [router],
  );

  return (
    <Screen contentContainerStyle={styles.content}>
      <Text accessibilityRole="header" style={[styles.title, { color: colors.text }]}>
        {t('search.title')}
      </Text>
      <View style={styles.entryRow}>
        <TextInput
          accessibilityLabel={t('search.input_label')}
          autoCapitalize="none"
          autoCorrect={false}
          onChangeText={(value) => {
            setText(value);
            setTooShort(false);
          }}
          onSubmitEditing={() => void submit(text)}
          placeholder={t('search.placeholder')}
          placeholderTextColor={colors.textMuted}
          returnKeyType="search"
          style={[
            styles.input,
            { color: colors.text, borderColor: colors.border, backgroundColor: colors.surface },
          ]}
          value={text}
        />
        <Pressable
          accessibilityRole="button"
          onPress={() => void submit(text)}
          style={({ pressed }) => [
            styles.actionButton,
            { backgroundColor: colors.primary, opacity: pressed ? 0.8 : 1 },
          ]}
        >
          <Text style={[styles.actionButtonText, { color: colors.onPrimary }]}>
            {t('search.submit')}
          </Text>
        </Pressable>
      </View>
      {showHint ? (
        <Text style={[styles.hint, { color: colors.textMuted }]}>{t('search.min_chars_hint')}</Text>
      ) : null}
      {recent.length > 0 ? (
        <View style={styles.recent}>
          <Text style={[styles.recentTitle, { color: colors.text }]}>
            {t('search.recent_title')}
          </Text>
          {recent.map((term) => (
            <Pressable
              key={term}
              accessibilityRole="button"
              onPress={() => void submit(term)}
              style={({ pressed }) => [
                styles.recentRow,
                { borderColor: colors.border, opacity: pressed ? 0.8 : 1 },
              ]}
            >
              <Text style={[styles.recentText, { color: colors.text }]}>{term}</Text>
            </Pressable>
          ))}
        </View>
      ) : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  content: { padding: spacing.lg, gap: spacing.md },
  title: { fontSize: typography.size.xl, fontWeight: typography.weight.bold },
  entryRow: { flexDirection: 'row', gap: spacing.sm },
  input: {
    flex: 1,
    minHeight: 52,
    borderWidth: 1,
    borderRadius: radii.md,
    paddingHorizontal: spacing.md,
    fontSize: typography.size.md,
  },
  actionButton: {
    minHeight: 52,
    justifyContent: 'center',
    paddingHorizontal: spacing.lg,
    borderRadius: radii.md,
  },
  actionButtonText: { fontSize: typography.size.sm, fontWeight: typography.weight.semibold },
  hint: { fontSize: typography.size.sm },
  recent: { gap: spacing.sm },
  recentTitle: { fontSize: typography.size.md, fontWeight: typography.weight.semibold },
  recentRow: {
    minHeight: 48,
    justifyContent: 'center',
    paddingHorizontal: spacing.md,
    borderWidth: 1,
    borderRadius: radii.md,
  },
  recentText: { fontSize: typography.size.md },
});
