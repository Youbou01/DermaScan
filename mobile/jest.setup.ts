// Runs before every test file. Gives the typed env (src/config/env.ts) a valid, offline default
// so tests never depend on a developer's local .env file.
process.env.EXPO_PUBLIC_API_URL ??= 'http://localhost:8000';
process.env.EXPO_PUBLIC_USE_MOCKS ??= 'false';

jest.mock('@react-native-async-storage/async-storage', () =>
  jest.requireActual('@react-native-async-storage/async-storage/jest/async-storage-mock'),
);
