import { columnsForWindow } from './ProductList';

jest.mock('@/api/product-list', () => ({ useProductListQuery: jest.fn() }));

describe('columnsForWindow', () => {
  it('uses one column in portrait', () => {
    expect(columnsForWindow(390, 844)).toBe(1);
  });

  it('uses two columns in landscape', () => {
    expect(columnsForWindow(844, 390)).toBe(2);
  });

  it('uses one column on a square window', () => {
    expect(columnsForWindow(600, 600)).toBe(1);
  });
});
