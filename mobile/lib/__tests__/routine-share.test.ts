import { confirmedRoutineCopy, sharedRoutinePath } from '@/lib/routineShare';

describe('shared routine actions', () => {
  it('does not build a copy request until a destination is confirmed', () => {
    expect(confirmedRoutineCopy(null, true)).toBeNull();
    expect(confirmedRoutineCopy('morning', false)).toBeNull();
    expect(confirmedRoutineCopy('evening', true)).toEqual({
      destination_slot: 'evening',
      confirm_replace: true,
    });
  });

  it('encodes a share token in the app route path', () => {
    expect(sharedRoutinePath('a/b+c')).toBe('/shared-routine/a%2Fb%2Bc');
  });
});
