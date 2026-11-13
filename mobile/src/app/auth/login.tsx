import type { ReactElement } from 'react';
import { AuthScreen } from '@/features/auth/AuthScreen';

export default function LoginRoute(): ReactElement {
  return <AuthScreen initialMode="login" />;
}
