import type { ReactElement, ReactNode } from 'react';
import { Redirect, type Href } from 'expo-router';
import { Screen, Skeleton } from '@/components';
import { useAuth } from './AuthProvider';

interface RequireAuthProps {
  children: ReactNode;
}

export function RequireAuth({ children }: RequireAuthProps): ReactElement {
  const { isAuthenticated, isReady } = useAuth();
  if (!isReady)
    return (
      <Screen>
        <Skeleton height={48} />
      </Screen>
    );
  if (!isAuthenticated) return <Redirect href={'/auth/sign-in' as Href} />;
  return <>{children}</>;
}
