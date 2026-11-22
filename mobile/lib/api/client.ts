import { useSession } from '@/lib/session';
import type { Session } from './types';
export const API_BASE_URL =
  (process.env.EXPO_PUBLIC_API_URL ?? 'https://dermascan-iorj.onrender.com').replace(/\/$/, '') +
  '/api/v1';
export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public code = '',
  ) {
    super(message);
    this.name = 'ApiError';
  }
}
export function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'Something went wrong. Please try again.';
}
let refreshing: { userId: string; promise: Promise<void> } | null = null;
async function renew() {
  const original = useSession.getState().session;
  if (!original) throw new ApiError(401, 'Please sign in to continue.');
  try {
    const result = await request<{ access_token: string }>('/auth/refresh', {
      method: 'POST',
      body: { refresh_token: original.refresh_token },
    });
    if (useSession.getState().session === original)
      await useSession.getState().setSession({ ...original, access_token: result.access_token });
  } catch (error) {
    if (
      error instanceof ApiError &&
      error.status === 401 &&
      useSession.getState().session === original
    )
      await useSession.getState().setSession(null);
    throw error;
  }
}
type RequestOptions = {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE';
  body?: unknown;
  auth?: boolean;
  signal?: AbortSignal;
};
export async function request<T>(
  path: string,
  options: RequestOptions = {},
  retried = false,
): Promise<T> {
  const session = useSession.getState().session;
  if (options.auth && !session) throw new ApiError(401, 'Please sign in to continue.');
  const controller = new AbortController();
  const abort = () => controller.abort();
  options.signal?.addEventListener('abort', abort);
  if (options.signal?.aborted) controller.abort();
  const timer = setTimeout(abort, 60000);
  let response: Response;
  try {
    const isForm = options.body instanceof FormData;
    response = await fetch(API_BASE_URL + path, {
      method: options.method ?? 'GET',
      signal: controller.signal,
      headers: {
        Accept: 'application/json',
        'Accept-Language': 'en',
        ...(!isForm && options.body !== undefined ? { 'Content-Type': 'application/json' } : {}),
        ...(options.auth ? { Authorization: `Bearer ${session?.access_token}` } : {}),
      },
      body:
        options.body === undefined
          ? undefined
          : options.body instanceof FormData
            ? options.body
            : JSON.stringify(options.body),
    });
  } catch {
    throw new ApiError(
      0,
      controller.signal.aborted
        ? 'The request took too long. Please try again.'
        : 'Could not reach DermaScan. Check your connection and try again.',
    );
  } finally {
    clearTimeout(timer);
    options.signal?.removeEventListener('abort', abort);
  }
  if (options.auth && session?.user.id !== useSession.getState().session?.user.id) {
    throw new ApiError(401, 'Your account changed. Please try this action again.');
  }
  if (response.status === 401 && options.auth && !retried && session) {
    if (session.access_token === useSession.getState().session?.access_token) {
      if (!refreshing || refreshing.userId !== session.user.id) {
        const renewal = { userId: session.user.id, promise: renew() };
        refreshing = renewal;
        void renewal.promise
          .finally(() => {
            if (refreshing === renewal) refreshing = null;
          })
          .catch(() => {});
      }
      await refreshing.promise;
    }
    if (session.user.id !== useSession.getState().session?.user.id)
      throw new ApiError(401, 'Please sign in to continue.');
    return request<T>(path, options, true);
  }
  if (response.status === 401 && options.auth && retried)
    await useSession.getState().setSession(null);
  if (!response.ok) {
    const data: unknown = await response.json().catch(() => null);
    const code = typeof data === 'object' && data && 'type' in data ? String(data.type) : '';
    const messages: Record<number, string> = {
      401: 'Your sign-in has expired or the credentials are incorrect. Please sign in again.',
      403: 'You do not have access to this action.',
      404: 'That item could not be found.',
      409: 'This already exists. Check your entries and try again.',
      413: 'Choose a photo smaller than 10 MB.',
      415: 'Choose a JPEG, PNG or WebP photo.',
      422: 'Check your entries and try again.',
      429: 'Too many requests. Please try again shortly.',
    };
    throw new ApiError(
      response.status,
      messages[response.status] ?? 'DermaScan could not complete this request. Please try again.',
      code,
    );
  }
  // eslint-disable-next-line typescript/no-unsafe-type-assertion -- HTTP 204 intentionally has no payload; callers of no-content endpoints ignore the result.
  if (response.status === 204) return undefined as T;
  // eslint-disable-next-line typescript/no-unsafe-type-assertion -- T is supplied by the endpoint's API contract; generic response shapes cannot be validated here without endpoint schemas.
  return response.json() as Promise<T>;
}
export function queryString(values: Record<string, string | number | string[] | undefined | null>) {
  const parts: string[] = [];
  for (const [key, value] of Object.entries(values)) {
    if (value === undefined || value === null || value === '') continue;
    for (const item of Array.isArray(value) ? value : [value])
      parts.push(`${encodeURIComponent(key)}=${encodeURIComponent(item)}`);
  }
  return parts.length ? '?' + parts.join('&') : '';
}
export async function signIn(email: string, password: string, displayName?: string) {
  const session = await request<Session>(
    displayName === undefined ? '/auth/login' : '/auth/register',
    {
      method: 'POST',
      body: {
        email: email.trim().toLowerCase(),
        password,
        ...(displayName === undefined ? {} : { display_name: displayName.trim() }),
      },
    },
  );
  await useSession.getState().setSession(session);
}
