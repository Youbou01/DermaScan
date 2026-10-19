import { EnvError, MOCK_API_URL, parseEnv } from './env';

describe('parseEnv', () => {
  it('accepts a valid API URL and keeps mocks off by default', () => {
    expect(parseEnv({ apiUrl: 'http://192.168.1.20:8000', useMocks: undefined })).toEqual({
      apiUrl: 'http://192.168.1.20:8000',
      useMocks: false,
    });
  });

  it.each([
    ['https://api.example.com/', 'https://api.example.com'],
    ['http://localhost:8000/', 'http://localhost:8000'],
    ['HTTPS://API.EXAMPLE.COM', 'https://api.example.com'],
  ])('normalizes %s to %s', (input, expected) => {
    expect(parseEnv({ apiUrl: input, useMocks: 'false' }).apiUrl).toBe(expected);
  });

  it.each([
    ['not a url'],
    ['ftp://example.com'],
    ['http://localhost:8000/api/v1'],
    ['http://localhost:8000/?debug=1'],
  ])('rejects the API URL "%s"', (input) => {
    expect(() => parseEnv({ apiUrl: input, useMocks: 'false' })).toThrow(EnvError);
  });

  it('requires an API URL when mocks are off', () => {
    expect(() => parseEnv({ apiUrl: undefined, useMocks: 'false' })).toThrow(EnvError);
    expect(() => parseEnv({ apiUrl: '', useMocks: undefined })).toThrow(EnvError);
  });

  it('lets mocks run without an API URL, using a URL that can never resolve', () => {
    expect(parseEnv({ apiUrl: undefined, useMocks: 'true' })).toEqual({
      apiUrl: MOCK_API_URL,
      useMocks: true,
    });
  });

  it('rejects anything but "true" or "false" for the mocks flag', () => {
    expect(() => parseEnv({ apiUrl: 'http://localhost:8000', useMocks: 'yes' })).toThrow(EnvError);
    expect(() => parseEnv({ apiUrl: 'http://localhost:8000', useMocks: '1' })).toThrow(EnvError);
  });
});
