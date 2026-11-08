import AsyncStorage from '@react-native-async-storage/async-storage';

const RECENT_SEARCHES_KEY = 'recent-searches';
export const MAX_RECENT_SEARCHES = 5;

export async function loadRecentSearches(): Promise<string[]> {
  try {
    const raw = await AsyncStorage.getItem(RECENT_SEARCHES_KEY);
    const parsed: unknown = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed)
      ? parsed.filter((item): item is string => typeof item === 'string')
      : [];
  } catch {
    // A storage failure leaves the list empty; search still works.
    return [];
  }
}

export async function addRecentSearch(term: string): Promise<string[]> {
  const trimmed = term.trim();
  const current = await loadRecentSearches();
  if (trimmed.length < 2) return current;
  const next = [
    trimmed,
    ...current.filter((item) => item.toLocaleLowerCase() !== trimmed.toLocaleLowerCase()),
  ].slice(0, MAX_RECENT_SEARCHES);
  try {
    await AsyncStorage.setItem(RECENT_SEARCHES_KEY, JSON.stringify(next));
  } catch {
    // The list still updates for this session even when persistence is unavailable.
  }
  return next;
}
