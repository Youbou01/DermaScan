import { createInstance } from 'i18next';
import { initReactI18next, I18nextProvider } from 'react-i18next';
import { getLocales } from 'expo-localization';
import { useEffect, type ReactElement, type ReactNode } from 'react';
import { strings, type Locale } from './strings';

const i18n = createInstance();
type Key = keyof typeof strings.en;
type Values = Record<string, string | number>;
const deviceLanguage = getLocales()[0]?.languageCode;
const initialLocale: Locale = deviceLanguage?.toLowerCase().startsWith('fr') ? 'fr' : 'en';
void i18n.use(initReactI18next).init({
  resources: { en: { translation: strings.en }, fr: { translation: strings.fr } },
  lng: initialLocale,
  fallbackLng: 'en',
  interpolation: { escapeValue: false },
});
export function I18nProvider({
  children,
  locale,
}: {
  readonly children: ReactNode;
  readonly locale?: Locale;
}): ReactElement {
  useEffect(() => {
    if (locale) void i18n.changeLanguage(locale);
  }, [locale]);
  return <I18nextProvider i18n={i18n}>{children}</I18nextProvider>;
}
export function useI18n(): { locale: Locale; t: (key: Key, values?: Values) => string } {
  return {
    locale: i18n.language.toLowerCase().startsWith('fr') ? 'fr' : 'en',
    t: (key, values) => String(i18n.t(key, values)),
  };
}
