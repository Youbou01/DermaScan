import i18n, { initializeI18n, resources } from '@/lib/i18n/i18n';
import { getActiveLanguage, normalizeLanguage, setActiveLanguage } from '@/lib/i18n/language-state';

const featureTranslationKeys = [
  'library.savedTitle',
  'library.recentTitle',
  'library.savedHeading',
  'library.recentHeading',
  'library.save',
  'library.saved',
  'library.unsave',
  'library.removing',
  'library.emptySaved',
  'library.emptyRecent',
  'library.signIn',
  'library.browse',
  'library.retry',
  'library.viewProduct',
  'guidance.title',
  'guidance.subtitle',
  'guidance.verified',
  'guidance.notVerified',
  'guidance.source',
  'guidance.relatedProducts',
  'guidance.empty',
  'guidance.informationOnly',
  'routineShare.share',
  'routineShare.creating',
  'routineShare.activeLinks',
  'routineShare.expires',
  'routineShare.views',
  'routineShare.revoke',
  'routineShare.revoked',
  'routineShare.created',
  'routineShare.publicTitle',
  'routineShare.signIn',
  'routineShare.chooseSlot',
  'routineShare.morning',
  'routineShare.evening',
  'routineShare.replaceWarning',
  'routineShare.confirmCopy',
  'routineShare.copying',
  'routineShare.viewProduct',
  'routineShare.cancel',
  'routineShare.copied',
  'routineShare.copyError',
  'routineShare.expired',
  'routineShare.expiresAt',
  'routineShare.steps',
] as const;

function collectTranslationKeys(value: unknown, prefix = ''): string[] {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) return [];
  return Object.entries(value).flatMap(([key, child]) => {
    const path = prefix ? `${prefix}.${key}` : key;
    return typeof child === 'string' ? [path] : collectTranslationKeys(child, path);
  });
}

describe('i18n localization system', () => {
  it('normalizes various language strings correctly', () => {
    expect(normalizeLanguage('fr')).toBe('fr');
    expect(normalizeLanguage('fr-FR')).toBe('fr');
    expect(normalizeLanguage('FR')).toBe('fr');
    expect(normalizeLanguage('en')).toBe('en');
    expect(normalizeLanguage('en-US')).toBe('en');
    expect(normalizeLanguage('es')).toBe('en');
    expect(normalizeLanguage(null)).toBe('en');
    expect(normalizeLanguage(undefined)).toBe('en');
  });

  it('sets and gets active language state', () => {
    setActiveLanguage('fr');
    expect(getActiveLanguage()).toBe('fr');
    setActiveLanguage('en');
    expect(getActiveLanguage()).toBe('en');
  });

  it('translates English keys correctly', async () => {
    await initializeI18n('en');
    expect(i18n.t('app.title')).toBe('DermaScan');
    expect(i18n.t('common.language')).toBe('Language');
    expect(i18n.t('common.english')).toBe('English');
    expect(i18n.t('common.french')).toBe('French');
  });

  it('translates French keys correctly when switched', async () => {
    await initializeI18n('fr');
    expect(i18n.t('app.title')).toBe('DermaScan');
    expect(i18n.t('common.language')).toBe('Langue');
    expect(i18n.t('common.english')).toBe('Anglais');
    expect(i18n.t('common.french')).toBe('Français');
    expect(i18n.t('scan.title')).toBe('Scanner un produit');
    // switch back to en
    await initializeI18n('en');
  });

  it('resolves every library, guidance, and routine-share label in both locales', async () => {
    for (const language of ['en', 'fr'] as const) {
      await initializeI18n(language);
      for (const key of featureTranslationKeys) {
        expect(i18n.t(key)).not.toBe(key);
      }
    }
    await initializeI18n('en');
  });

  it('contains identical translation key structure between en and fr', () => {
    const enKeys = collectTranslationKeys(resources.en.translation).sort();
    const frKeys = collectTranslationKeys(resources.fr.translation).sort();
    expect(enKeys).toEqual(frKeys);
  });
});
