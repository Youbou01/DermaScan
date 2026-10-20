import en from './en.json';
import fr from './fr.json';

function keyStructure(value: unknown): unknown {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) return typeof value;
  return Object.fromEntries(
    Object.entries(value).map(([key, child]) => [key, keyStructure(child)]),
  );
}

describe('translation dictionaries', () => {
  it('contains the same key structure in English and French', () => {
    expect(keyStructure(fr)).toEqual(keyStructure(en));
  });
});
