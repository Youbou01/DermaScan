import { fireEvent, render, screen } from '@testing-library/react-native';
import { I18nProvider } from '@/i18n';
import { ThemeProvider } from '@/theme/theme';
import { ProductCard } from './index';
describe('ProductCard', () => {
  it('presses and exposes one useful card label with missing optional data', async () => {
    const onPress = jest.fn();
    await render(
      <ThemeProvider>
        <I18nProvider>
          <ProductCard name="A long moisturizer name" onPress={onPress} />
        </I18nProvider>
      </ThemeProvider>,
    );
    const card = screen.getByRole('button', { name: /A long moisturizer name/ });
    expect(card).toBeTruthy();
    await fireEvent.press(card);
    expect(onPress).toHaveBeenCalledTimes(1);
  });
});
