import { render } from '@testing-library/react-native';

import HomeRoute from '@/app/index';
import { I18nProvider } from '@/i18n';
import { ThemeProvider } from '@/theme/theme';

// Smoke test: proves jest-expo, Testing Library and the `@/` alias are wired up.
// Route files must stay in src/app, but their tests must NOT (Expo Router turns every file in
// src/app into a route), which is why this lives in src/__tests__/app.
describe('HomeRoute', () => {
  it('renders the placeholder title', async () => {
    // `await` works for both a sync and an async `render` (it changed between library versions).
    const screen = await render(
      <ThemeProvider>
        <I18nProvider>
          <HomeRoute />
        </I18nProvider>
      </ThemeProvider>,
    );
    expect(screen.getByText('Welcome to DermaScan')).toBeTruthy();
  });
});
