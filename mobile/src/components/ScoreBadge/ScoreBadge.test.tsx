import { fireEvent, render, screen } from '@testing-library/react-native';
import { I18nProvider } from '@/i18n';
import { ThemeProvider } from '@/theme/theme';
import { ScoreBadge } from './index';
import { ErrorState } from '@/components/ErrorState';
describe('ScoreBadge and ErrorState', () => {
  it('announces score band and insufficient data', async () => {
    await render(
      <ThemeProvider>
        <I18nProvider>
          <ScoreBadge score={72} band="moderate" />
          <ScoreBadge />
        </I18nProvider>
      </ThemeProvider>,
    );
    expect(screen.getByLabelText('Safety score 72 out of 100, Moderate concern')).toBeTruthy();
    expect(screen.getByLabelText('Not enough data')).toBeTruthy();
  });
  it('calls retry', async () => {
    const retry = jest.fn();
    await render(
      <ThemeProvider>
        <I18nProvider>
          <ErrorState onRetry={retry} />
        </I18nProvider>
      </ThemeProvider>,
    );
    await fireEvent.press(screen.getByRole('button', { name: 'Try again' }));
    expect(retry).toHaveBeenCalledTimes(1);
  });
});
