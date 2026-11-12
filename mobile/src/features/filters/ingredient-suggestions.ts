// MOCK: there is no ingredient autocomplete endpoint yet. Replace this list with the API when it exists.
export const MOCK_INGREDIENT_NAMES: readonly string[] = [
  'Aqua',
  'Glycerin',
  'Cetearyl Alcohol',
  'Niacinamide',
  'Panthenol',
  'Sodium Hyaluronate',
  'Squalane',
  'Phenoxyethanol',
  'Citric Acid',
  'Parfum',
];

function simplify(text: string): string {
  return text
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .trim();
}

export function suggestIngredients(query: string, limit = 5): string[] {
  const key = simplify(query);
  if (key === '') return [];
  return MOCK_INGREDIENT_NAMES.filter((name) => simplify(name).includes(key)).slice(0, limit);
}
