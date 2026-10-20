import { fireEvent, render } from '@testing-library/react-native';

import { LanguageSwitch } from '@/components/LanguageSwitch';
import { i18n, setLanguage } from '@/i18n';

afterEach(async () => {
  await setLanguage('en');
});

describe('LanguageSwitch', () => {
  it('switches the app language when a language is pressed', async () => {
    const screen = await render(<LanguageSwitch />);
    await fireEvent.press(screen.getByRole('radio', { name: 'Français' }));
    expect(i18n.language).toBe('fr');
    expect(screen.getByRole('radio', { name: 'Français', selected: true })).toBeTruthy();
  });
});
