import type { CopySharedRoutineRequest, Slot } from '@/lib/api/types';

export function confirmedRoutineCopy(
  destinationSlot: Slot | null,
  confirmed: boolean,
): CopySharedRoutineRequest | null {
  if (!destinationSlot || !confirmed) return null;
  return { destination_slot: destinationSlot, confirm_replace: true };
}

export function sharedRoutinePath(token: string): string {
  return `/shared-routine/${encodeURIComponent(token)}`;
}
