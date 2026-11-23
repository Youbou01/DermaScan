import i18n, { initializeI18n, resources } from '@/lib/i18n/i18n';
import { getActiveLanguage, normalizeLanguage, setActiveLanguage } from '@/lib/i18n/language-state';

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

  it('contains identical translation key structure between en and fr', () => {
    const enKeys = Object.keys(resources.en.translation).sort();
    const frKeys = Object.keys(resources.fr.translation).sort();
    expect(enKeys).toEqual(frKeys);
  });
});
