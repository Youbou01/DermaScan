import { fireEvent, render } from '@testing-library/react-native';
import { useProductListQuery } from '@/api/product-list';
import { ProductList } from '@/components';
import i18n from '@/i18n/i18n';

jest.mock('@/api/product-list', () => ({ useProductListQuery: jest.fn() }));

type ListResult = ReturnType<typeof useProductListQuery>;

const cleanser = {
  id: 'p1',
  name: 'Gentle Cleanser',
  brand: 'Demo',
  image_url: null,
  score: 72,
  score_band: 'low' as const,
  category_slug: 'cleanser',
};
const serum = { ...cleanser, id: 'p2', name: 'Hydration Serum', category_slug: 'serum' };

function mockList(overrides: Record<string, unknown>): void {
  jest.mocked(useProductListQuery).mockReturnValue({
    isPending: false,
    isError: false,
    isFetchingNextPage: false,
    isFetchNextPageError: false,
    hasNextPage: false,
    data: undefined,
    refetch: jest.fn(),
    fetchNextPage: jest.fn(),
    ...overrides,
  } as unknown as ListResult);
}

function pages(...itemsPerPage: (typeof cleanser)[][]): unknown {
  return {
    pages: itemsPerPage.map((items) => ({ items, next_cursor: null })),
    pageParams: itemsPerPage.map(() => undefined),
  };
}

describe('ProductList', () => {
  it('shows loading skeletons while the first page loads', async () => {
    mockList({ isPending: true });
    const screen = await render(<ProductList />);
    expect(screen.getAllByLabelText(i18n.t('common.loading')).length).toBeGreaterThan(0);
  });

  it('shows an error state and retries', async () => {
    const refetch = jest.fn();
    mockList({ isError: true, refetch });
    const screen = await render(<ProductList />);

    await fireEvent.press(screen.getByText(i18n.t('common.retry')));
    expect(refetch).toHaveBeenCalledTimes(1);
  });

  it('shows an empty state when there are no products', async () => {
    mockList({ data: pages([]) });
    const screen = await render(<ProductList />);
    expect(screen.getByText(i18n.t('productList.empty_title'))).toBeTruthy();
  });

  it('renders the products and reports presses with the product id', async () => {
    const onProductPress = jest.fn();
    mockList({ data: pages([cleanser, serum]) });
    const screen = await render(<ProductList onProductPress={onProductPress} />);

    expect(screen.getByText('Hydration Serum')).toBeTruthy();
    await fireEvent.press(screen.getByText('Gentle Cleanser'));
    expect(onProductPress).toHaveBeenCalledWith('p1');
  });

  it('shows a product once when two pages contain it', async () => {
    mockList({ data: pages([cleanser], [cleanser, serum]) });
    const screen = await render(<ProductList />);
    expect(screen.getAllByText('Gentle Cleanser')).toHaveLength(1);
  });

  it('loads the next page at the end of the list only when there is one', async () => {
    const fetchNextPage = jest.fn();
    mockList({ data: pages([cleanser]), hasNextPage: true, fetchNextPage });
    const screen = await render(<ProductList />);
    await fireEvent(screen.getByTestId('product-list'), 'endReached');
    expect(fetchNextPage).toHaveBeenCalledTimes(1);

    const none = jest.fn();
    mockList({ data: pages([cleanser]), hasNextPage: false, fetchNextPage: none });
    const last = await render(<ProductList />);
    await fireEvent(last.getByTestId('product-list'), 'endReached');
    expect(none).not.toHaveBeenCalled();
  });

  it('offers a retry when loading the next page fails', async () => {
    const fetchNextPage = jest.fn();
    mockList({
      data: pages([cleanser]),
      hasNextPage: true,
      isFetchNextPageError: true,
      fetchNextPage,
    });
    const screen = await render(<ProductList />);

    expect(screen.getByText(i18n.t('productList.load_more_failed'))).toBeTruthy();
    await fireEvent.press(screen.getByText(i18n.t('common.retry')));
    expect(fetchNextPage).toHaveBeenCalledTimes(1);
  });
});
