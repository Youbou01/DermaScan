import { productCardsFixture } from './fixtures';

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
