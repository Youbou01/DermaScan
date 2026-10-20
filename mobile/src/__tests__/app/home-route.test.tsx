import { render } from '@testing-library/react-native';

import HomeRoute from '@/app/index';
import { i18n } from '@/i18n';

describe('HomeRoute', () => {
  it('renders the translated title and the language switch', async () => {
    const screen = await render(<HomeRoute />);
    expect(screen.getByText(i18n.t('home.title'))).toBeTruthy();
    expect(screen.getByRole('radio', { name: 'English' })).toBeTruthy();
  });
});
