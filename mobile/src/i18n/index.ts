import AsyncStorage from '@react-native-async-storage/async-storage';
import { getLocales } from 'expo-localization';
import { createInstance } from 'i18next';
import { initReactI18next } from 'react-i18next';

import en from './en.json';
import fr from './fr.json';

const STORAGE_KEY = 'app.language';
const SUPPORTED = ['en', 'fr'] as const;
export type Language = (typeof SUPPORTED)[number];

function isLanguage(code: string | null | undefined): code is Language {
  return SUPPORTED.some((lang) => lang === code);
}

const deviceLanguage = getLocales()[0]?.languageCode;

export const i18n = createInstance();

void i18n.use(initReactI18next).init({
  resources: { en: { translation: en }, fr: { translation: fr } },
  lng: isLanguage(deviceLanguage) ? deviceLanguage : 'en',
  fallbackLng: 'en',
  interpolation: { escapeValue: false },
});

// Restore the user's manual choice, if any.
void AsyncStorage.getItem(STORAGE_KEY).then((saved) => {
  if (isLanguage(saved)) void i18n.changeLanguage(saved);
});

export async function setLanguage(lang: Language): Promise<void> {
  await AsyncStorage.setItem(STORAGE_KEY, lang);
  await i18n.changeLanguage(lang);
}

export function currentLanguage(): Language {
  return isLanguage(i18n.language) ? i18n.language : 'en';
}
