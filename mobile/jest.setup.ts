import { initializeI18n } from './lib/i18n/i18n';
import mockAsyncStorage from '@react-native-async-storage/async-storage/jest/async-storage-mock';

jest.mock('@react-native-async-storage/async-storage', () => mockAsyncStorage);
jest.mock('expo-localization', () => ({
  getLocales: () => [{ languageCode: 'en', languageTag: 'en-US' }],
}));

// Set default test environment variables
process.env.EXPO_PUBLIC_API_URL ??= 'http://localhost:8000';
process.env.EXPO_PUBLIC_USE_MOCKS ??= 'false';

beforeAll(async () => {
  await initializeI18n('en');
});
