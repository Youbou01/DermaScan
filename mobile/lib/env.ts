/**
 * Validated environment configuration for DermaScan Mobile.
 *
 * Rules:
 * - Defaults to local backend development (`http://localhost:8000`).
 * - To point to the deployed cloud backend, set `EXPO_PUBLIC_USE_CLOUD_BACKEND=true`
 *   or provide `EXPO_PUBLIC_API_URL=https://dermascan-iorj.onrender.com`.
 * - Validates URL format and normalizes trailing slashes and redundant `/api/v1` paths.
 */

export const DEFAULT_LOCAL_API_URL = 'http://localhost:8000';
export const CLOUD_API_URL = 'https://dermascan-iorj.onrender.com';
export const MOCK_API_URL = 'https://mock.invalid';

export interface Env {
  /** The backend origin URL without trailing slash or `/api/v1`. */
  readonly apiUrl: string;
  /** Full base URL including `/api/v1`. */
  readonly apiBaseUrl: string;
  /** True if targeting the deployed cloud backend on Render. */
  readonly isCloud: boolean;
  /** Serve offline fixtures/mocks instead of calling live backend. */
  readonly useMocks: boolean;
}

export interface RawEnv {
  readonly apiUrl?: string;
  readonly useCloud?: string;
  readonly useMocks?: string;
}

export class EnvError extends Error {
  constructor(message: string) {
    super(`[Invalid Environment] ${message} See mobile/.env.example for valid configuration.`);
    this.name = 'EnvError';
  }
}

function parseBoolean(name: string, value: string | undefined): boolean {
  if (value === undefined || value === '' || value.toLowerCase() === 'false') {
    return false;
  }
  if (value.toLowerCase() === 'true') {
    return true;
  }
  throw new EnvError(`${name} must be "true" or "false", got "${value}".`);
}

function normalizeUrl(value: string): string {
  let cleaned = value.trim();
  // Strip trailing slash
  cleaned = cleaned.replace(/\/+$/, '');
  // If user accidentally included /api/v1 in the origin, strip it cleanly
  if (cleaned.endsWith('/api/v1')) {
    cleaned = cleaned.slice(0, -'/api/v1'.length).replace(/\/+$/, '');
  }

  let parsed: URL;
  try {
    parsed = new URL(cleaned);
  } catch {
    throw new EnvError(`EXPO_PUBLIC_API_URL is not a valid URL: "${value}".`);
  }

  if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') {
    throw new EnvError(`EXPO_PUBLIC_API_URL must start with http:// or https://, got "${value}".`);
  }

  return `${parsed.protocol}//${parsed.host}`;
}

export function parseEnv(raw: RawEnv): Env {
  const useMocks = parseBoolean('EXPO_PUBLIC_USE_MOCKS', raw.useMocks);
  const useCloud = parseBoolean('EXPO_PUBLIC_USE_CLOUD_BACKEND', raw.useCloud);

  let apiUrl: string;
  if (raw.apiUrl !== undefined && raw.apiUrl.trim() !== '') {
    apiUrl = normalizeUrl(raw.apiUrl);
  } else if (useCloud) {
    apiUrl = CLOUD_API_URL;
  } else if (useMocks) {
    apiUrl = MOCK_API_URL;
  } else {
    // Default to local backend
    apiUrl = DEFAULT_LOCAL_API_URL;
  }

  return {
    apiUrl,
    apiBaseUrl: `${apiUrl}/api/v1`,
    isCloud: apiUrl === CLOUD_API_URL || apiUrl.includes('onrender.com'),
    useMocks,
  };
}

export const env: Env = parseEnv({
  apiUrl: process.env.EXPO_PUBLIC_API_URL,
  useCloud: process.env.EXPO_PUBLIC_USE_CLOUD_BACKEND,
  useMocks: process.env.EXPO_PUBLIC_USE_MOCKS,
});
