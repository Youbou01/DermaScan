import { env } from '@/config/env';

export function resolveProductImageUrl(rawUrl: string | null | undefined): string | null {
  if (!rawUrl || !rawUrl.trim()) {
    return null;
  }
  try {
    const parsed = new URL(rawUrl);
    if (parsed.hostname === 'localhost' || parsed.hostname === '127.0.0.1') {
      const apiParsed = new URL(env.apiUrl);
      if (
        apiParsed.hostname &&
        apiParsed.hostname !== 'localhost' &&
        apiParsed.hostname !== '127.0.0.1' &&
        apiParsed.hostname !== 'mock.invalid'
      ) {
        parsed.hostname = apiParsed.hostname;
        return parsed.toString();
      }
    }
    return parsed.toString();
  } catch {
    return rawUrl;
  }
}
