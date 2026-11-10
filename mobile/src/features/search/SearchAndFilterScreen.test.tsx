import type { ReactElement } from 'react';
import { fireEvent, render, waitFor } from '@testing-library/react-native';
import { LanguageProvider } from '@/i18n/LanguageProvider';
import { categoriesFixture as mockCategories } from '@/api/fixtures';
import { searchFixture as mockSearchFixture } from '@/api/search-fixture';
import { SearchAndFilterScreen } from './SearchAndFilterScreen';

const mockSearch = jest.fn();
let mockCategory: string | undefined;
let mockInfiniteResult: Record<string, unknown>;
jest.mock('expo-router', () => ({
  useLocalSearchParams: () => ({ category: mockCategory }),
  useRouter: () => ({ push: jest.fn() }),
}));
jest.mock('@/api/hooks', () => {
  return {
    useCategoriesQuery: () => ({ data: mockCategories.en }),
    useProductSearchInfiniteQuery: (...args: unknown[]) => {
      mockSearch(...args);
      return mockInfiniteResult;
    },
  };
});

function renderScreen(): ReactElement {
  return (
    <LanguageProvider>
      <SearchAndFilterScreen />
    </LanguageProvider>
  );
}

describe('SearchAndFilterScreen', () => {
  beforeEach(() => {
    mockSearch.mockClear();
    mockCategory = undefined;
    mockInfiniteResult = {
      data: {
        pages: [mockSearchFixture],
        pageParams: [null],
      },
      isPending: false,
      isError: false,
      hasNextPage: false,
      isFetchingNextPage: false,
      fetchNextPage: jest.fn(),
      refetch: jest.fn(),
    };
  });

  it('renders translated filters and results and applies a category from navigation', async () => {
    mockCategory = 'serum';
    const screen = await render(renderScreen());
    expect(screen.getByLabelText('Search by product name')).toBeTruthy();
    expect(screen.getByText('Daily Hydration Serum')).toBeTruthy();
    await waitFor(() =>
      expect(mockSearch).toHaveBeenLastCalledWith(
        '',
        expect.objectContaining({ category: 'serum' }),
      ),
    );
    expect(screen.getByRole('button', { name: 'Low concern' })).toBeTruthy();
  });

  it('supports category, risk band, and ingredient include/avoid controls', async () => {
    const screen = await render(renderScreen());
    await fireEvent.press(screen.getByRole('button', { name: 'Serum' }));
    await fireEvent.press(screen.getByRole('button', { name: 'Low concern' }));
    await fireEvent.press(screen.getByRole('button', { name: 'Include ingredient' }));
    await fireEvent.changeText(screen.getByLabelText('Ingredient name'), 'Glycerin');
    await fireEvent.press(screen.getByRole('button', { name: 'Add' }));
    await waitFor(() =>
      expect(mockSearch).toHaveBeenLastCalledWith(
        '',
        expect.objectContaining({ category: 'serum', band: ['low'], include: ['Glycerin'] }),
      ),
    );
  });

  it('announces loading, empty, and retryable error states', async () => {
    mockCategory = 'serum';
    mockInfiniteResult = {
      data: undefined,
      isPending: true,
      isError: false,
      hasNextPage: false,
      isFetchingNextPage: false,
      fetchNextPage: jest.fn(),
      refetch: jest.fn(),
    };
    const loading = await render(renderScreen());
    expect(loading.getByLabelText('Loading products')).toBeTruthy();

    mockInfiniteResult = {
      data: { pages: [{ items: [], next_cursor: null }], pageParams: [null] },
      isPending: false,
      isError: false,
      hasNextPage: false,
      isFetchingNextPage: false,
      fetchNextPage: jest.fn(),
      refetch: jest.fn(),
    };
    const empty = await render(renderScreen());
    expect(empty.getByText('No matching products')).toBeTruthy();

    mockInfiniteResult = {
      data: undefined,
      isPending: false,
      isError: true,
      error: new Error('offline'),
      hasNextPage: false,
      isFetchingNextPage: false,
      fetchNextPage: jest.fn(),
      refetch: jest.fn(),
    };
    const failed = await render(renderScreen());
    expect(failed.getByText('Something went wrong')).toBeTruthy();
    expect(failed.getByRole('button', { name: 'Try again' })).toBeTruthy();
  });
});
