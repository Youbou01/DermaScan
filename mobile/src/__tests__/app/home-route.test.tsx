import { fireEvent, render, waitFor } from '@testing-library/react-native';
import i18n from '@/i18n/i18n';
import { LanguageProvider } from '@/i18n/LanguageProvider';

import HomeRoute from '@/app/index';

// Smoke test: proves jest-expo, Testing Library and the `@/` alias are wired up.
// Route files must stay in src/app, but their tests must NOT (Expo Router turns every file in
// src/app into a route), which is why this lives in src/__tests__/app.
describe('HomeRoute', () => {
  it('renders its title as an accessible header', async () => {
    // `await` works for both a sync and an async `render` (it changed between library versions).
    const screen = await render(
      <LanguageProvider>
        <HomeRoute />
      </LanguageProvider>,
    );
    expect(screen.getByRole('header', { name: i18n.t('app.title') })).toBeTruthy();
    await fireEvent.press(screen.getByRole('button', { name: i18n.t('common.french') }));
    await waitFor(() => {
      expect(screen.getByText(i18n.t('app.open_design_system'))).toBeTruthy();
    });
  });
});
