import { render, screen } from '@testing-library/react-native';
import { I18nProvider } from '@/i18n';
import { ThemeProvider } from '@/theme/theme';
import { Skeleton } from './index';
describe('Skeleton', () => {
  it.each(['block', 'line', 'product'] as const)(
    'renders %s without animation when reduced motion is requested',
    async (variant) => {
      await render(
        <ThemeProvider>
          <I18nProvider>
            <Skeleton variant={variant} reduceMotion />
          </I18nProvider>
        </ThemeProvider>,
      );
      expect(screen.getByLabelText('Loading')).toBeTruthy();
    },
  );
});
