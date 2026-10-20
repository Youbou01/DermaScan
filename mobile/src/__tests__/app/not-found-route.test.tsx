import { render } from '@testing-library/react-native';

import NotFoundRoute from '@/app/+not-found';

describe('NotFoundRoute', () => {
  it('announces the error as a header and exposes an accessible home link', async () => {
    const screen = await render(<NotFoundRoute />);

    expect(screen.getByRole('header', { name: 'This screen does not exist.' })).toBeTruthy();
    expect(screen.getByRole('link', { name: 'Go to the home screen' })).toBeTruthy();
  });
});
