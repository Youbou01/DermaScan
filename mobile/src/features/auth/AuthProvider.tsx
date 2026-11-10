import AsyncStorage from '@react-native-async-storage/async-storage';
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import type { ReactElement, ReactNode } from 'react';
import { env } from '@/config/env';
import type { AuthSession, AuthUser } from '@/api/contracts';
import { setAccessToken } from '@/api/client';
import { ApiContractUnavailableError } from '@/api/hooks';

const SESSION_KEY = 'auth-session';
const demoUser: AuthUser = {
  id: '01950000-0000-7000-8000-000000000001',
  email: 'demo@dermascan.app',
  display_name: 'Sara',
};
const localAccounts = new Map<string, { password: string; user: AuthUser }>([
  [demoUser.email, { password: 'DermaScan123!', user: demoUser }],
]);

interface AuthContextValue {
  readonly user: AuthUser | null;
  readonly isAuthenticated: boolean;
  readonly isReady: boolean;
  signIn(email: string, password: string): Promise<void>;
  signUp(email: string, password: string, displayName: string): Promise<void>;
  signOut(): Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

function sessionFor(user: AuthUser): AuthSession {
  return {
    access_token: `mock-access-${user.id}`,
    refresh_token: `mock-refresh-${user.id}`,
    token_type: 'bearer',
    user,
  };
}

export function AuthProvider({ children }: { children: ReactNode }): ReactElement {
  const [session, setSession] = useState<AuthSession | null>(null);
  const [isReady, setReady] = useState(false);

  useEffect(() => {
    let active = true;
    void AsyncStorage.getItem(SESSION_KEY)
      .then((raw) => {
        if (!active) return;
        if (raw) {
          try {
            const restored = JSON.parse(raw) as AuthSession;
            setSession(restored);
            setAccessToken(restored.access_token);
          } catch {
            void AsyncStorage.removeItem(SESSION_KEY);
          }
        }
        setReady(true);
      })
      .catch(() => {
        if (active) setReady(true);
      });
    return () => {
      active = false;
    };
  }, []);

  const saveSession = useCallback(async (next: AuthSession): Promise<void> => {
    setSession(next);
    setAccessToken(next.access_token);
    await AsyncStorage.setItem(SESSION_KEY, JSON.stringify(next));
  }, []);

  const signUp = useCallback(
    async (email: string, password: string, displayName: string): Promise<void> => {
      if (!env.useMocks)
        throw new ApiContractUnavailableError(
          'Registration is not yet available in the backend OpenAPI contract.',
        );
      const normalizedEmail = email.trim().toLocaleLowerCase();
      if (localAccounts.has(normalizedEmail))
        throw Object.assign(new Error('An account already exists for this email.'), {
          status: 409,
        });
      const user = {
        id: `mock-user-${Date.now()}`,
        email: normalizedEmail,
        display_name: displayName.trim(),
      };
      localAccounts.set(normalizedEmail, { password, user });
      await saveSession(sessionFor(user));
    },
    [saveSession],
  );

  const signIn = useCallback(
    async (email: string, password: string): Promise<void> => {
      if (!env.useMocks)
        throw new ApiContractUnavailableError(
          'Sign-in is not yet available in the backend OpenAPI contract.',
        );
      const account = localAccounts.get(email.trim().toLocaleLowerCase());
      if (!account || account.password !== password)
        throw Object.assign(new Error('Email or password is incorrect.'), { status: 401 });
      await saveSession(sessionFor(account.user));
    },
    [saveSession],
  );

  const signOut = useCallback(async (): Promise<void> => {
    setSession(null);
    setAccessToken(null);
    await AsyncStorage.removeItem(SESSION_KEY);
  }, []);

  const value = useMemo(
    () => ({
      user: session?.user ?? null,
      isAuthenticated: session !== null,
      isReady,
      signIn,
      signUp,
      signOut,
    }),
    [session, isReady, signIn, signUp, signOut],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within AuthProvider');
  return context;
}
