import { getActiveLanguage, setActiveLanguage, type Language } from '@/i18n/language-state';

export type ApiLocale = Language;

/** Called by the i18n language-change handler so requests follow the visible app language. */
export function setApiLocale(locale: string): void {
  setActiveLanguage(locale.toLowerCase().startsWith('fr') ? 'fr' : 'en');
}

export function getActiveApiLocale(): ApiLocale {
  return getActiveLanguage();
}
