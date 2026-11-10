import type { ReactElement } from 'react';
import { ProfileScreen } from '@/features/profile/ProfileScreen';
import { RequireAuth } from '@/features/auth/RequireAuth';

export default function ProfileRoute(): ReactElement {
  return (
    <RequireAuth>
      <ProfileScreen />
    </RequireAuth>
  );
}
