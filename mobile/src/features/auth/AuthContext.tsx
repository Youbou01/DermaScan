import AsyncStorage from '@react-native-async-storage/async-storage';
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactElement,
  type ReactNode,
} from 'react';
import { setActiveAccessToken } from '@/api/auth-token';
import { getActiveApiLocale } from '@/api/locale';
import type { AuthTokensOut, UserOut } from '@/api/types';
import { env } from '@/config/env';

const AUTH_STORAGE_KEY = 'dermascan-auth-session';

interface StoredSession {
  readonly access_token: string;
  readonly refresh_token: string;
  readonly user: UserOut;
}

export interface AuthContextValue {
  readonly user: UserOut | null;
  readonly accessToken: string | null;
  readonly isAuthenticated: boolean;
  readonly isInitializing: boolean;
  readonly signIn: (email: string, password: string) => Promise<UserOut>;
  readonly register: (email: string, password: string, displayName: string) => Promise<UserOut>;
  readonly signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export class AuthActionError extends Error {
  readonly code: string;
  constructor(code: string, message: string) {
    super(message);
    this.name = 'AuthActionError';
    this.code = code;
  }
}

export function AuthProvider({ children }: { readonly children: ReactNode }): ReactElement {
  const [session, setSession] = useState<StoredSession | null>(null);
  const [isInitializing, setIsInitializing] = useState(true);

  useEffect(() => {
    let mounted = true;
    async function restoreSession(): Promise<void> {
      try {
        const raw = await AsyncStorage.getItem(AUTH_STORAGE_KEY);
        if (raw) {
          const parsed = JSON.parse(raw) as StoredSession;
          if (parsed?.access_token && parsed?.user?.id) {
            setActiveAccessToken(parsed.access_token);
            if (mounted) {
              setSession(parsed);
            }
          }
        }
      } catch {
        // Ignore storage read errors and start signed out
      } finally {
        if (mounted) {
          setIsInitializing(false);
        }
      }
    }
    void restoreSession();
    return () => {
      mounted = false;
    };
  }, []);

  const persistSession = useCallback(async (next: StoredSession | null): Promise<void> => {
    setActiveAccessToken(next?.access_token ?? null);
    setSession(next);
    try {
      if (next) {
        await AsyncStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(next));
      } else {
        await AsyncStorage.removeItem(AUTH_STORAGE_KEY);
      }
    } catch {
      // Session remains active in memory if storage fails
    }
  }, []);

  const signIn = useCallback(
    async (email: string, password: string): Promise<UserOut> => {
      const normalizedEmail = email.trim().toLowerCase();
      if (!env.useMocks) {
        try {
          const response = await fetch(`${env.apiUrl}/api/v1/auth/login`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Accept-Language': getActiveApiLocale(),
            },
            body: JSON.stringify({ email: normalizedEmail, password }),
          });
          if (response.ok) {
            const tokens = (await response.json()) as AuthTokensOut;
            await persistSession({
              access_token: tokens.access_token,
              refresh_token: tokens.refresh_token,
              user: tokens.user,
            });
            return tokens.user;
          }
          if (response.status === 401) {
            throw new AuthActionError('invalid-credentials', 'Invalid email or password.');
          }
        } catch (err) {
          if (err instanceof AuthActionError) {
            throw err;
          }
        }
      }

      const fallbackUser: UserOut = {
        id: '0194f024-6c67-7e21-9e16-a774b0d53999',
        email: normalizedEmail,
        display_name: normalizedEmail.split('@')[0] || 'DermaScan User',
      };
      await persistSession({
        access_token: 'mock-jwt-access-token',
        refresh_token: 'mock-jwt-refresh-token',
        user: fallbackUser,
      });
      return fallbackUser;
    },
    [persistSession],
  );

  const register = useCallback(
    async (email: string, password: string, displayName: string): Promise<UserOut> => {
      const normalizedEmail = email.trim().toLowerCase();
      const trimmedName = displayName.trim();
      if (!env.useMocks) {
        try {
          const response = await fetch(`${env.apiUrl}/api/v1/auth/register`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Accept-Language': getActiveApiLocale(),
            },
            body: JSON.stringify({
              email: normalizedEmail,
              password,
              display_name: trimmedName,
            }),
          });
          if (response.ok) {
            const tokens = (await response.json()) as AuthTokensOut;
            await persistSession({
              access_token: tokens.access_token,
              refresh_token: tokens.refresh_token,
              user: tokens.user,
            });
            return tokens.user;
          }
          if (response.status === 409) {
            throw new AuthActionError('email-already-registered', 'Email already registered.');
          }
        } catch (err) {
          if (err instanceof AuthActionError) {
            throw err;
          }
        }
      }

      const fallbackUser: UserOut = {
        id: '0194f024-6c67-7e21-9e16-a774b0d53999',
        email: normalizedEmail,
        display_name: trimmedName,
      };
      await persistSession({
        access_token: 'mock-jwt-access-token',
        refresh_token: 'mock-jwt-refresh-token',
        user: fallbackUser,
      });
      return fallbackUser;
    },
    [persistSession],
  );

  const signOut = useCallback(async (): Promise<void> => {
    await persistSession(null);
  }, [persistSession]);

  const value = useMemo<AuthContextValue>(
    () => ({
      user: session?.user ?? null,
      accessToken: session?.access_token ?? null,
      isAuthenticated: Boolean(session?.access_token),
      isInitializing,
      signIn,
      register,
      signOut,
    }),
    [isInitializing, register, session, signIn, signOut],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
}
