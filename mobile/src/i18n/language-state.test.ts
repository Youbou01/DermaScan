import * as Localization from 'expo-localization';
import { detectDeviceLanguage, normalizeLanguage } from './language-state';

describe('device language detection', () => {
  beforeEach(() => {
    jest
      .spyOn(Localization, 'getLocales')
      .mockReturnValue([
        { languageCode: 'fr' } as ReturnType<typeof Localization.getLocales>[number],
      ]);
  });

  it('selects French for a French device locale', () => {
    expect(detectDeviceLanguage()).toBe('fr');
  });

  it('defaults all non-French locales to English', () => {
    expect(normalizeLanguage('ar-TN')).toBe('en');
    expect(normalizeLanguage('en-GB')).toBe('en');
    expect(normalizeLanguage(undefined)).toBe('en');
  });
});
