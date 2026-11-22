import { create } from 'zustand';
import { z } from 'zod';
import type { Session } from '@/lib/api/types';
import { readSession, writeSession, removeSession } from '@/lib/sessionStorage';
const schema = z.object({
  access_token: z.string(),
  refresh_token: z.string(),
  user: z.object({ id: z.string(), email: z.string(), display_name: z.string() }),
});
type SessionState = {
  session: Session | null;
  ready: boolean;
  storageError: string | null;
  initialize: () => Promise<void>;
  setSession: (session: Session | null) => Promise<void>;
};
export const useSession = create<SessionState>((set) => ({
  session: null,
  ready: false,
  storageError: null,
  initialize: async () => {
    try {
      const raw = await readSession();
      const result = raw ? schema.safeParse(JSON.parse(raw)) : null;
      set({ session: result?.success ? result.data : null, ready: true });
    } catch {
      set({
        ready: true,
        storageError: 'Your saved sign-in could not be opened. Please sign in again.',
      });
    }
  },
  setSession: async (session) => {
    if (session) {
      await writeSession(JSON.stringify(session));
      set({ session, storageError: null });
    } else {
      await removeSession();
      set({ session: null });
    }
  },
}));
