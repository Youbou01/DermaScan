import type { ReactElement } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, waitFor } from '@testing-library/react-native';
import i18n from '@/i18n/i18n';
import { LanguageProvider } from '@/i18n/LanguageProvider';
import { AuthProvider } from './AuthContext';
import { AuthScreen } from './AuthScreen';

const mockPush = jest.fn();
const mockReplace = jest.fn();

jest.mock('expo-router', () => ({
  useRouter: () => ({ push: mockPush, replace: mockReplace }),
}));

function renderAuth(initialMode: 'login' | 'register' = 'login'): ReactElement {
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
          <AuthScreen initialMode={initialMode} />
        </LanguageProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}

describe('AuthScreen (US-09)', () => {
  beforeEach(() => {
    mockPush.mockClear();
    mockReplace.mockClear();
  });

  it('validates email and password length before submitting', async () => {
    const screen = await render(renderAuth('login'));
    await screen.findByText(i18n.t('auth.sign_in_title'));

    await fireEvent.press(screen.getByRole('button', { name: i18n.t('auth.sign_in_button') }));

    expect(screen.getByRole('alert')).toBeTruthy();
    expect(screen.getByText(i18n.t('auth.validation_error'))).toBeTruthy();
  });

  it('switches to register mode, creates an account, and redirects to /profile', async () => {
    const screen = await render(renderAuth('login'));
    await screen.findByText(i18n.t('auth.sign_in_title'));

    await fireEvent.press(screen.getByRole('button', { name: i18n.t('auth.switch_to_register') }));
    expect(screen.getByText(i18n.t('auth.register_title'))).toBeTruthy();

    await fireEvent.changeText(
      screen.getByLabelText(i18n.t('auth.display_name_label')),
      'Sara Ben Ali',
    );
    await fireEvent.changeText(
      screen.getByLabelText(i18n.t('auth.email_label')),
      'sara@example.com',
    );
    await fireEvent.changeText(
      screen.getByLabelText(i18n.t('auth.password_label')),
      'password1234',
    );

    await fireEvent.press(screen.getByRole('button', { name: i18n.t('auth.register_button') }));

    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith('/profile');
    });
  });
});
