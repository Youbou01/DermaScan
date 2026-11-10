import type { ProductFilterParams, ProductPage } from './hooks';
import { productCardsFixture, productFixture } from './fixtures';

const searchProducts: ProductPage['items'] = productCardsFixture.map((product, index) => ({
  id: product.id,
  barcode: `61900000000${19 + index}`,
  name: product.name,
  brand: product.brand,
  image_url: product.image_url,
  score: product.score,
  score_band: product.score_band ?? 'unknown',
}));

export const searchFixture: ProductPage = { items: searchProducts, next_cursor: null };

export function findMockSearchResults(query: string): ProductPage {
  const normalizedQuery = query.trim().toLocaleLowerCase();
  return {
    items: searchFixture.items.filter((product) =>
      `${product.name} ${product.brand ?? ''}`.toLocaleLowerCase().includes(normalizedQuery),
    ),
    next_cursor: null,
  };
}

export function findMockFilterResults(filters: ProductFilterParams): ProductPage {
  const selectedBands = filters.band ?? [];
  const included = filters.include?.map((name) => name.toLocaleLowerCase()) ?? [];
  const excluded = filters.exclude?.map((name) => name.toLocaleLowerCase()) ?? [];
  return {
    items: searchFixture.items.filter((product) => {
      const card = productCardsFixture.find((item) => item.id === product.id);
      if (filters.category && card?.category_slug !== filters.category) return false;
      if (selectedBands.length > 0 && !selectedBands.some((band) => band === product.score_band))
        return false;
      const ingredientNames =
        product.id === productFixture.id
          ? productFixture.ingredients
              .flatMap((ingredient) => [ingredient.name, ingredient.inci_name ?? ''])
              .join(' ')
          : '';
      const corpus =
        `${product.name} ${product.brand ?? ''} ${ingredientNames}`.toLocaleLowerCase();
      if (included.some((name) => !corpus.includes(name))) return false;
      return !excluded.some((name) => corpus.includes(name));
    }),
    next_cursor: null,
  };
}
