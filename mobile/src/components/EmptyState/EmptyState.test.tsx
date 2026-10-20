import { fireEvent, render, screen } from '@testing-library/react-native';
import { I18nProvider } from '@/i18n';
import { ThemeProvider } from '@/theme/theme';
import { EmptyState } from './index';
describe('EmptyState', () => {
  it('shows localized defaults and calls an optional action', async () => {
    const action = jest.fn();
    await render(
      <ThemeProvider>
        <I18nProvider>
          <EmptyState actionLabel="Browse products" onAction={action} />
        </I18nProvider>
      </ThemeProvider>,
    );
    expect(screen.getByText('Nothing here yet')).toBeTruthy();
    await fireEvent.press(screen.getByRole('button', { name: 'Browse products' }));
    expect(action).toHaveBeenCalledTimes(1);
  });
});
