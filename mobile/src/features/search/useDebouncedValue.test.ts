import { act, renderHook } from '@testing-library/react-native';
import { useDebouncedValue } from './useDebouncedValue';

describe('useDebouncedValue', () => {
  beforeEach(() => {
    jest.useFakeTimers();
  });
  afterEach(() => {
    jest.useRealTimers();
  });

  it('returns the initial value immediately', async () => {
    const { result } = await renderHook(() => useDebouncedValue('a', 300));
    expect(result.current).toBe('a');
  });

  it('updates only after the delay has passed without changes', async () => {
    const { result, rerender } = await renderHook(
      ({ value }: { value: string }) => useDebouncedValue(value, 300),
      { initialProps: { value: 'c' } },
    );
    await rerender({ value: 'cr' });
    await act(async () => {
      jest.advanceTimersByTime(299);
    });
    expect(result.current).toBe('c');
    await act(async () => {
      jest.advanceTimersByTime(1);
    });
    expect(result.current).toBe('cr');
  });

  it('restarts the delay on every change and keeps only the last value', async () => {
    const { result, rerender } = await renderHook(
      ({ value }: { value: string }) => useDebouncedValue(value, 300),
      { initialProps: { value: 'c' } },
    );
    await rerender({ value: 'cr' });
    await act(async () => {
      jest.advanceTimersByTime(200);
    });
    await rerender({ value: 'cre' });
    await act(async () => {
      jest.advanceTimersByTime(200);
    });
    expect(result.current).toBe('c');
    await act(async () => {
      jest.advanceTimersByTime(100);
    });
    expect(result.current).toBe('cre');
  });
});
