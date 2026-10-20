import type { ReactElement } from 'react';
import { Link } from 'expo-router';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { useTranslation } from '@/i18n/useTranslation';
import { useLanguage } from '@/i18n/LanguageProvider';
import { useThemeColors } from '@/theme/tokens';

export default function HomeRoute(): ReactElement {
  const { t } = useTranslation();
  const { currentLanguage, setLanguage } = useLanguage();
  const colors = useThemeColors();
  return (
    <View style={styles.container}>
      <Text accessibilityRole="header" style={styles.title}>
        {t('app.title')}
      </Text>
      <View style={styles.languagePicker}>
        <Text style={[styles.languageLabel, { color: colors.textMuted }]}>
          {t('common.language')}
        </Text>
        <View style={styles.languageOptions}>
          {(['en', 'fr'] as const).map((language) => (
            <Pressable
              key={language}
              accessibilityRole="button"
              accessibilityState={{ selected: currentLanguage === language }}
              onPress={() => void setLanguage(language)}
              style={[
                styles.languageButton,
                {
                  backgroundColor: currentLanguage === language ? colors.primary : colors.surface,
                  borderColor: colors.primary,
                },
              ]}
            >
              <Text
                style={{
                  color: currentLanguage === language ? colors.onPrimary : colors.text,
                  fontWeight: '600',
                }}
              >
                {t(language === 'en' ? 'common.english' : 'common.french')}
              </Text>
            </Pressable>
          ))}
        </View>
      </View>
      {__DEV__ ? (
        <Link href="/design-system" asChild>
          <Pressable accessibilityRole="button" style={styles.showcaseButton}>
            <Text style={styles.showcaseText}>{t('app.open_design_system')}</Text>
          </Pressable>
        </Link>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  title: { fontSize: 28, fontWeight: '600' },
  languagePicker: { alignItems: 'center', gap: 8, marginTop: 24 },
  languageLabel: { fontSize: 14 },
  languageOptions: { flexDirection: 'row', gap: 8 },
  languageButton: {
    minHeight: 44,
    minWidth: 96,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 14,
    borderWidth: 1,
    borderRadius: 12,
  },
  showcaseButton: {
    minHeight: 44,
    marginTop: 20,
    justifyContent: 'center',
    paddingHorizontal: 16,
    borderRadius: 12,
    backgroundColor: '#246B50',
  },
  showcaseText: { color: '#FFFFFF', fontSize: 16, fontWeight: '600' },
});
