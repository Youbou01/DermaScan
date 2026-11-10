import type { ReactElement } from 'react';
import { AuthForm } from './AuthForm';

export function SignInScreen(): ReactElement {
  return <AuthForm mode="sign-in" />;
}
