export type ApiLocale = 'en' | 'fr';

function deviceLocale(): ApiLocale {
  const languageCode = Intl.DateTimeFormat().resolvedOptions().locale.toLowerCase();
  return languageCode.startsWith('fr') ? 'fr' : 'en';
}

let activeLocale: ApiLocale = deviceLocale();

/** Called by the i18n language-change handler so requests follow the visible app language. */
export function setApiLocale(locale: string): void {
  activeLocale = locale.toLowerCase().startsWith('fr') ? 'fr' : 'en';
}

export function getActiveApiLocale(): ApiLocale {
  return activeLocale;
}
