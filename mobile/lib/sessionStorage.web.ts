// Browser credentials remain in memory; a reload requires sign-in again.
let value: string | null = null;
export const readSession = () => Promise.resolve(value);
export const writeSession = (next: string) => {
  value = next;
  return Promise.resolve();
};
export const removeSession = () => {
  value = null;
  return Promise.resolve();
};
