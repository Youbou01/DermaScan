let activeAccessToken: string | null = null;

export function setActiveAccessToken(token: string | null): void {
  activeAccessToken = token;
}

export function getActiveAccessToken(): string | null {
  return activeAccessToken;
}

export function buildAuthHeaders(extra: Record<string, string> = {}): Record<string, string> {
  const headers: Record<string, string> = { ...extra };
  if (activeAccessToken) {
    headers.Authorization = `Bearer ${activeAccessToken}`;
  }
  return headers;
}
