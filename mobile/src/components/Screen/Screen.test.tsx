import { render, screen } from '@testing-library/react-native';
import { I18nProvider } from '@/i18n';
import { ThemeProvider } from '@/theme/theme';
import { Screen } from './index';
import { Text } from 'react-native';
describe('Screen', () => {
  it('renders its header and children inside the shared wrapper', async () => {
    await render(
      <ThemeProvider>
        <I18nProvider>
          <Screen title="Products">
            <Text>Content</Text>
          </Screen>
        </I18nProvider>
      </ThemeProvider>,
    );
    expect(screen.getByRole('header', { name: 'Products' })).toBeTruthy();
    expect(screen.getByText('Content')).toBeTruthy();
  });
});
