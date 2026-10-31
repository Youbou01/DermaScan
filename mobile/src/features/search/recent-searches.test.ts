import AsyncStorage from '@react-native-async-storage/async-storage';
import { MAX_RECENT_SEARCHES, addRecentSearch, loadRecentSearches } from './recent-searches';

describe('recent searches', () => {
  beforeEach(async () => {
    await AsyncStorage.clear();
  });

  it('starts empty', async () => {
    expect(await loadRecentSearches()).toEqual([]);
  });

  it('stores the newest search first', async () => {
    await addRecentSearch('creme');
    const list = await addRecentSearch('serum');
    expect(list).toEqual(['serum', 'creme']);
    expect(await loadRecentSearches()).toEqual(['serum', 'creme']);
  });

  it('moves a repeated search to the top without duplicating it', async () => {
    await addRecentSearch('creme');
    await addRecentSearch('serum');
    expect(await addRecentSearch('CREME')).toEqual(['CREME', 'serum']);
  });

  it('ignores terms shorter than 2 characters', async () => {
    expect(await addRecentSearch(' a ')).toEqual([]);
  });

  it('keeps only the latest entries', async () => {
    for (let i = 0; i < MAX_RECENT_SEARCHES + 2; i += 1) {
      await addRecentSearch(`term ${i}`);
    }
    const list = await loadRecentSearches();
    expect(list).toHaveLength(MAX_RECENT_SEARCHES);
    expect(list[0]).toBe(`term ${MAX_RECENT_SEARCHES + 1}`);
  });

  it('returns an empty list when the stored value is not valid JSON', async () => {
    await AsyncStorage.setItem('recent-searches', '{not json');
    expect(await loadRecentSearches()).toEqual([]);
  });
});
