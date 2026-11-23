import { getLocales } from 'expo-localization';

export type Language = 'en' | 'fr';

let activeLanguage: Language = detectDeviceLanguage();

export function normalizeLanguage(language: string | null | undefined): Language {
  return language?.toLowerCase().startsWith('fr') ? 'fr' : 'en';
}

export function detectDeviceLanguage(): Language {
  try {
    const locales = getLocales();
    const locale = locales && locales.length > 0 ? locales[0] : null;
    return normalizeLanguage(locale?.languageCode ?? locale?.languageTag);
  } catch {
    return 'en';
  }
}

export function setActiveLanguage(language: Language): void {
  activeLanguage = language;
}

export function getActiveLanguage(): Language {
  return activeLanguage;
}
