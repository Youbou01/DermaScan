import { CLOUD_API_URL, DEFAULT_LOCAL_API_URL, EnvError, MOCK_API_URL, parseEnv } from '@/lib/env';

describe('parseEnv', () => {
  it('defaults to local backend when no environment variables are set', () => {
    const parsed = parseEnv({});
    expect(parsed.apiUrl).toBe(DEFAULT_LOCAL_API_URL);
    expect(parsed.apiBaseUrl).toBe('http://localhost:8000/api/v1');
    expect(parsed.isCloud).toBe(false);
    expect(parsed.useMocks).toBe(false);
  });

  it('connects to deployed cloud backend when EXPO_PUBLIC_USE_CLOUD_BACKEND is true', () => {
    const parsed = parseEnv({ useCloud: 'true' });
    expect(parsed.apiUrl).toBe(CLOUD_API_URL);
    expect(parsed.apiBaseUrl).toBe('https://dermascan-iorj.onrender.com/api/v1');
    expect(parsed.isCloud).toBe(true);
    expect(parsed.useMocks).toBe(false);
  });

  it('allows custom API URL and normalizes trailing slashes', () => {
    const parsed = parseEnv({ apiUrl: 'http://192.168.1.50:8000///' });
    expect(parsed.apiUrl).toBe('http://192.168.1.50:8000');
    expect(parsed.apiBaseUrl).toBe('http://192.168.1.50:8000/api/v1');
    expect(parsed.isCloud).toBe(false);
  });

  it('strips redundant /api/v1 suffix if accidentally supplied in EXPO_PUBLIC_API_URL', () => {
    const parsed = parseEnv({ apiUrl: 'http://localhost:8000/api/v1' });
    expect(parsed.apiUrl).toBe('http://localhost:8000');
    expect(parsed.apiBaseUrl).toBe('http://localhost:8000/api/v1');
  });

  it('supports explicit cloud URL override', () => {
    const parsed = parseEnv({ apiUrl: 'https://dermascan-iorj.onrender.com' });
    expect(parsed.apiUrl).toBe(CLOUD_API_URL);
    expect(parsed.isCloud).toBe(true);
  });

  it('enables mock mode when EXPO_PUBLIC_USE_MOCKS is true', () => {
    const parsed = parseEnv({ useMocks: 'true' });
    expect(parsed.useMocks).toBe(true);
    expect(parsed.apiUrl).toBe(MOCK_API_URL);
    expect(parsed.apiBaseUrl).toBe('https://mock.invalid/api/v1');
  });

  it('throws EnvError for malformed URLs', () => {
    expect(() => parseEnv({ apiUrl: 'not-a-valid-url' })).toThrow(EnvError);
  });

  it('throws EnvError for invalid protocols (not http or https)', () => {
    expect(() => parseEnv({ apiUrl: 'ftp://localhost:8000' })).toThrow(EnvError);
  });

  it('throws EnvError for non-boolean useCloud or useMocks', () => {
    expect(() => parseEnv({ useCloud: 'yes' })).toThrow(EnvError);
    expect(() => parseEnv({ useMocks: '1' })).toThrow(EnvError);
  });
});
