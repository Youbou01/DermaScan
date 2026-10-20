import en from './en.json';
import fr from './fr.json';

function flatKeys(value: Record<string, unknown>, prefix = ''): string[] {
  return Object.entries(value).flatMap(([key, child]) =>
    typeof child === 'object' && child !== null
      ? flatKeys(child as Record<string, unknown>, `${prefix}${key}.`)
      : [`${prefix}${key}`],
  );
}

describe('translations', () => {
  it('have exactly the same keys in English and French', () => {
    expect(flatKeys(fr).sort()).toEqual(flatKeys(en).sort());
  });

  it('give every risk level a label, with unknown worded as insufficient data', () => {
    expect(Object.keys(en.risk).sort()).toEqual(['high', 'low', 'moderate', 'unknown']);
    expect(en.risk.unknown).toBe('Insufficient data');
    expect(fr.risk.unknown).toBe('Données insuffisantes');
  });
});
