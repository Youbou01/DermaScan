import { productCardsFixture } from './fixtures';
import type { ProductCard } from './types';

/** Search is described by docs/search-api-contract.md but is not yet in backend OpenAPI. */
export const searchFixture = {
  items: productCardsFixture,
  next_cursor: null,
};

export function findMockSearchResults(query: string): typeof searchFixture {
  const normalizedQuery = query.trim().toLocaleLowerCase();
  return {
    items: searchFixture.items.filter((product) =>
      `${product.name} ${product.brand ?? ''}`.toLocaleLowerCase().includes(normalizedQuery),
    ),
    next_cursor: null,
  };
}

export interface MockProductPage {
  items: ProductCard[];
  next_cursor: string | null;
}

/** Paginated mock list: the cursor is the numeric offset of the next page. */
export function findMockProductPage(
  filters: { query?: string; category?: string },
  cursor: string | undefined,
  limit: number,
): MockProductPage {
  const normalizedQuery = (filters.query ?? '').trim().toLocaleLowerCase();
  const matches = productCardsFixture.filter((product) => {
    const textMatch =
      normalizedQuery.length < 2 ||
      `${product.name} ${product.brand ?? ''}`.toLocaleLowerCase().includes(normalizedQuery);
    const categoryMatch = !filters.category || product.category_slug === filters.category;
    return textMatch && categoryMatch;
  });
  const parsed = Number(cursor ?? 0);
  const offset = Number.isInteger(parsed) && parsed >= 0 ? parsed : 0;
  const end = offset + limit;
  return {
    items: matches.slice(offset, end),
    next_cursor: end < matches.length ? String(end) : null,
  };
}
