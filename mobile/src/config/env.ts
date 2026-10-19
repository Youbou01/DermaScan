/**
 * The ONLY place that reads environment variables. Everything else imports `env` from here.
 *
 * Rules that make this file look the way it does:
 * - Expo inlines `process.env.EXPO_PUBLIC_*` at build time, but only for the literal expression
 *   `process.env.EXPO_PUBLIC_NAME`. Dynamic access (`process.env[name]`) is undefined in the app.
 * - Everything EXPO_PUBLIC_* is readable by anyone who unpacks the app: never a secret.
 * - A bad value must fail at startup with a clear message, not at the first network call.
 */

export interface Env {
  /** Backend root without `/api/v1` and without a trailing slash. */
  readonly apiUrl: string;
  /** Serve fixtures instead of calling the backend. */
  readonly useMocks: boolean;
}

export interface RawEnv {
  readonly apiUrl: string | undefined;
  readonly useMocks: string | undefined;
}

export class EnvError extends Error {
  constructor(message: string) {
    super(`Invalid environment: ${message} See mobile/.env.example.`);
    this.name = 'EnvError';
  }
}

/**
 * Used when mocks are on and no API URL is set. The `.invalid` top-level domain is reserved
 * (RFC 6761) and can never resolve, so a request that accidentally escapes the mock layer fails
 * loudly instead of hitting a real server.
 */
export const MOCK_API_URL = 'https://mock.invalid';

function parseBoolean(name: string, value: string | undefined): boolean {
  if (value === undefined || value === '' || value === 'false') {
    return false;
  }
  if (value === 'true') {
    return true;
  }
  throw new EnvError(`${name} must be "true" or "false", got "${value}".`);
}

function parseApiUrl(value: string | undefined, useMocks: boolean): string {
  if (value === undefined || value === '') {
    if (useMocks) {
      return MOCK_API_URL;
    }
    throw new EnvError('EXPO_PUBLIC_API_URL is required (or set EXPO_PUBLIC_USE_MOCKS=true).');
  }

  let url: URL;
  try {
    url = new URL(value);
  } catch {
    throw new EnvError(`EXPO_PUBLIC_API_URL is not a valid URL: "${value}".`);
  }
  if (url.protocol !== 'http:' && url.protocol !== 'https:') {
    throw new EnvError(`EXPO_PUBLIC_API_URL must start with http:// or https://, got "${value}".`);
  }
  if (url.pathname !== '/' || url.search !== '' || url.hash !== '') {
    throw new EnvError(
      `EXPO_PUBLIC_API_URL must be the server root, without a path ("/api/v1" is added by the client), got "${value}".`,
    );
  }
  return url.origin;
}

/** Pure and exported for tests: turns raw strings into a validated `Env`. */
export function parseEnv(raw: RawEnv): Env {
  const useMocks = parseBoolean('EXPO_PUBLIC_USE_MOCKS', raw.useMocks);
  return { apiUrl: parseApiUrl(raw.apiUrl, useMocks), useMocks };
}

export const env: Env = parseEnv({
  apiUrl: process.env.EXPO_PUBLIC_API_URL,
  useMocks: process.env.EXPO_PUBLIC_USE_MOCKS,
});
