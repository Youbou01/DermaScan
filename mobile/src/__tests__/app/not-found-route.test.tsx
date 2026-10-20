import { render } from '@testing-library/react-native';
import i18n from '@/i18n/i18n';

import NotFoundRoute from '@/app/+not-found';

describe('NotFoundRoute', () => {
  it('announces the error as a header and exposes an accessible home link', async () => {
    const screen = await render(<NotFoundRoute />);

    expect(screen.getByRole('header', { name: i18n.t('errors.not_found_title') })).toBeTruthy();
    expect(screen.getByRole('link', { name: i18n.t('errors.go_home') })).toBeTruthy();
  });
});
