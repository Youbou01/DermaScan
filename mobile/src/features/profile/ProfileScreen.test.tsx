import type { ReactElement } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, waitFor } from '@testing-library/react-native';
import i18n from '@/i18n/i18n';
import { AuthProvider } from '@/features/auth/AuthContext';
import { LanguageProvider } from '@/i18n/LanguageProvider';
import { resetMockProfileStore } from './profile-api';
import { ProfileScreen } from './ProfileScreen';

const mockPush = jest.fn();

jest.mock('expo-router', () => ({
  useRouter: () => ({ push: mockPush }),
}));

function renderProfile(): ReactElement {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: false, gcTime: 0 },
    },
  });
  return (
    <QueryClientProvider client={client}>
      <AuthProvider>
        <LanguageProvider>
          <ProfileScreen />
        </LanguageProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}

describe('ProfileScreen (US-11, US-12, US-14)', () => {
  beforeEach(() => {
    resetMockProfileStore();
    mockPush.mockClear();
  });

  it('selects skin type, dermatological condition, and saves health profile', async () => {
    const screen = await render(renderProfile());
    await screen.findByText(i18n.t('profile.title'));

    await fireEvent.press(
      screen.getByRole('button', { name: i18n.t('profile.skin_types.sensitive') }),
    );
    await fireEvent.press(
      screen.getByRole('button', { name: i18n.t('profile.conditions.eczema') }),
    );

    await fireEvent.press(screen.getByRole('button', { name: i18n.t('profile.save_button') }));

    await waitFor(() => {
      expect(screen.getByText(i18n.t('profile.saved_confirmation'))).toBeTruthy();
    });
  });

  it('toggles an ingredient in the blacklist', async () => {
    const screen = await render(renderProfile());
    await screen.findByText(i18n.t('profile.title'));

    const parfumBlacklistBtn = screen.getByRole('button', {
      name: 'Blacklist: Parfum / Fragrance',
    });
    await fireEvent.press(parfumBlacklistBtn);

    await waitFor(() => {
      expect(
        screen.getByRole('button', { name: 'Blacklist: Parfum / Fragrance' }).props
          .accessibilityState?.selected,
      ).toBe(true);
    });
  });
});
