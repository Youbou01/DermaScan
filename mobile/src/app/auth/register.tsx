import type { ReactElement } from 'react';
import { AuthScreen } from '@/features/auth/AuthScreen';

export default function RegisterRoute(): ReactElement {
  return <AuthScreen initialMode="register" />;
}
