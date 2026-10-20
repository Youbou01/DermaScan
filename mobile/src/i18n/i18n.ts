import { createInstance } from 'i18next';
import { initReactI18next } from 'react-i18next';
import en from './en.json';
import fr from './fr.json';
import { detectDeviceLanguage, type Language } from './language-state';

export const resources = { en: { translation: en }, fr: { translation: fr } } as const;
const i18n = createInstance();

declare module 'i18next' {
  interface CustomTypeOptions {
    defaultNS: 'translation';
    resources: typeof resources.en;
  }
}

let initialization: Promise<void> | null = null;

export function initializeI18n(language: Language = detectDeviceLanguage()): Promise<void> {
  if (!initialization) {
    initialization = i18n
      .use(initReactI18next)
      .init({
        resources,
        lng: language,
        fallbackLng: 'en',
        supportedLngs: ['en', 'fr'],
        defaultNS: 'translation',
        interpolation: { escapeValue: false },
        react: { useSuspense: false },
        returnNull: false,
      })
      .then(() => undefined);
  }
  const pendingInitialization = initialization;
  if (pendingInitialization === null) throw new Error('i18next initialization did not start');
  return pendingInitialization.then(async () => {
    if (i18n.language !== language) await i18n.changeLanguage(language);
  });
}

export default i18n;
