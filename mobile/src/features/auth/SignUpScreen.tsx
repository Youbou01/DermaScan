import type { ReactElement } from 'react';
import { AuthForm } from './AuthForm';

export function SignUpScreen(): ReactElement {
  return <AuthForm mode="sign-up" />;
}
