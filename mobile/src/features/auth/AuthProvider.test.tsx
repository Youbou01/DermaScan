import type { ReactElement } from 'react';
import { Pressable, Text, View } from 'react-native';
import { fireEvent, render, waitFor } from '@testing-library/react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import type { AuthSession } from '@/api/contracts';
import { AuthProvider, useAuth } from './AuthProvider';

jest.mock('@/config/env', () => ({ env: { apiUrl: 'https://mock.invalid', useMocks: true } }));

function Consumer({ email }: { email: string }): ReactElement {
  const auth = useAuth();
  return (
    <View>
      <Text>{auth.user?.email ?? 'visitor'}</Text>
      <Text>{auth.isReady ? 'ready' : 'loading'}</Text>
      <Pressable
        accessibilityRole="button"
        onPress={() => auth.signUp(email, 'password123', 'Sara')}
      >
        <Text>sign-up-action</Text>
      </Pressable>
      <Pressable accessibilityRole="button" onPress={() => auth.signIn(email, 'password123')}>
        <Text>sign-in-action</Text>
      </Pressable>
      <Pressable accessibilityRole="button" onPress={() => auth.signOut()}>
        <Text>sign-out-action</Text>
      </Pressable>
    </View>
  );
}

describe('AuthProvider mock lifecycle', () => {
  beforeEach(async () => {
    await AsyncStorage.clear();
  });

  it('supports sign-up, sign-in, and sign-out', async () => {
    const screen = await render(
      <AuthProvider>
        <Consumer email="sara@example.com" />
      </AuthProvider>,
    );
    await waitFor(() => expect(screen.getByText('ready')).toBeTruthy());
    await fireEvent.press(screen.getByRole('button', { name: 'sign-up-action' }));
    await waitFor(() => expect(screen.getByText('sara@example.com')).toBeTruthy());
    await fireEvent.press(screen.getByRole('button', { name: 'sign-out-action' }));
    await waitFor(() => expect(screen.getByText('visitor')).toBeTruthy());
    await fireEvent.press(screen.getByRole('button', { name: 'sign-in-action' }));
    await waitFor(() => expect(screen.getByText('sara@example.com')).toBeTruthy());
    await fireEvent.press(screen.getByRole('button', { name: 'sign-out-action' }));
    await waitFor(() => expect(screen.getByText('visitor')).toBeTruthy());
  });

  it('restores the stored session after the provider is recreated', async () => {
    const session: AuthSession = {
      access_token: 'stored-access',
      refresh_token: 'stored-refresh',
      token_type: 'bearer',
      user: { id: 'stored-user', email: 'restore@example.com', display_name: 'Sara' },
    };
    await AsyncStorage.setItem('auth-session', JSON.stringify(session));
    const screen = await render(
      <AuthProvider>
        <Consumer email="restore@example.com" />
      </AuthProvider>,
    );
    await waitFor(() => expect(screen.getByText('ready')).toBeTruthy());
    expect(screen.getByText('restore@example.com')).toBeTruthy();
  });
});
