import AsyncStorage from '@react-native-async-storage/async-storage';
import { fireEvent, render, waitFor } from '@testing-library/react-native';
import i18n from '@/i18n/i18n';
import { SearchScreen } from './SearchScreen';
import { addRecentSearch, loadRecentSearches } from './recent-searches';

const mockPush = jest.fn();

jest.mock('expo-router', () => ({
  useRouter: () => ({ push: mockPush }),
}));

describe('SearchScreen', () => {
  beforeEach(async () => {
    mockPush.mockClear();
    await AsyncStorage.clear();
  });

  it('shows a hint and does not navigate when the field is empty', async () => {
    const screen = await render(<SearchScreen />);
    await fireEvent.press(screen.getByRole('button', { name: i18n.t('search.submit') }));
    expect(await screen.findByText(i18n.t('search.min_chars_hint'))).toBeTruthy();
    expect(mockPush).not.toHaveBeenCalled();
  });

  it('opens the product list with the typed text and saves it as a recent search', async () => {
    const screen = await render(<SearchScreen />);
    await fireEvent.changeText(screen.getByLabelText(i18n.t('search.input_label')), 'creme');
    await fireEvent.press(screen.getByRole('button', { name: i18n.t('search.submit') }));
    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith({ pathname: '/products', params: { q: 'creme' } });
    });
    expect(await loadRecentSearches()).toEqual(['creme']);
  });

  it('trims spaces around the typed text', async () => {
    const screen = await render(<SearchScreen />);
    await fireEvent.changeText(screen.getByLabelText(i18n.t('search.input_label')), '  creme  ');
    await fireEvent(screen.getByLabelText(i18n.t('search.input_label')), 'submitEditing');
    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith({ pathname: '/products', params: { q: 'creme' } });
    });
  });

  it('lists recent searches and searches again when one is pressed', async () => {
    await addRecentSearch('serum');
    const screen = await render(<SearchScreen />);
    expect(await screen.findByText(i18n.t('search.recent_title'))).toBeTruthy();
    await fireEvent.press(screen.getByRole('button', { name: 'serum' }));
    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith({ pathname: '/products', params: { q: 'serum' } });
    });
  });

  it('shows the hint after the debounce delay when only one character is typed', async () => {
    const screen = await render(<SearchScreen />);
    await fireEvent.changeText(screen.getByLabelText(i18n.t('search.input_label')), 'a');
    expect(await screen.findByText(i18n.t('search.min_chars_hint'))).toBeTruthy();
    expect(mockPush).not.toHaveBeenCalled();
  });
});
