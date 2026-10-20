import { getLocales } from 'expo-localization';

export type Language = 'en' | 'fr';

let activeLanguage: Language = detectDeviceLanguage();

export function normalizeLanguage(language: string | null | undefined): Language {
  return language?.toLowerCase().startsWith('fr') ? 'fr' : 'en';
}

export function detectDeviceLanguage(): Language {
  const locale = getLocales()[0];
  return normalizeLanguage(locale?.languageCode ?? locale?.languageTag);
}

export function setActiveLanguage(language: Language): void {
  activeLanguage = language;
}

export function getActiveLanguage(): Language {
  return activeLanguage;
}
