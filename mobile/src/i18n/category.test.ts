import { getLocalizedCategory, getLocalizedCategorySlug } from './category';

describe('getLocalizedCategory', () => {
  it('returns the translation for a known backend slug', () => {
    expect(getLocalizedCategory({ slug: 'cleanser', name: 'API cleanser name' }, 'fr')).toBe(
      'Nettoyant',
    );
  });

  it('falls back to the API name for a missing slug translation', () => {
    expect(
      getLocalizedCategory({ slug: 'new-backend-category', name: 'Custom category' }, 'fr'),
    ).toBe('Custom category');
  });

  it('does not expose an unknown machine slug as a category label', () => {
    expect(getLocalizedCategorySlug('new-backend-category', 'en')).toBeNull();
  });
});
