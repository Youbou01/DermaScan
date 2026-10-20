import type { ReactElement } from 'react';
import { useTranslation } from 'react-i18next';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { setLanguage, type Language } from '@/i18n';

const LANGUAGES: readonly Language[] = ['en', 'fr'];

export function LanguageSwitch(): ReactElement {
  const { t, i18n } = useTranslation();

  return (
    <View
      accessibilityRole="radiogroup"
      accessibilityLabel={t('language.title')}
      style={styles.row}
    >
      {LANGUAGES.map((lang) => {
        const selected = i18n.language === lang;
        return (
          <Pressable
            key={lang}
            accessibilityRole="radio"
            accessibilityState={{ selected }}
            onPress={() => {
              void setLanguage(lang);
            }}
            style={[styles.button, selected && styles.buttonSelected]}
          >
            <Text style={selected ? styles.labelSelected : styles.label}>
              {t(`language.${lang}`)}
            </Text>
          </Pressable>
        );
      })}
    </View>
  );
}

// The selected language is shown with a thicker border AND bold text, not colour alone.
const styles = StyleSheet.create({
  row: { flexDirection: 'row', gap: 12 },
  button: {
    minWidth: 44,
    minHeight: 44,
    paddingHorizontal: 16,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 8,
    borderWidth: 1,
  },
  buttonSelected: { borderWidth: 3 },
  label: { fontSize: 16 },
  labelSelected: { fontSize: 16, fontWeight: '700' },
});
