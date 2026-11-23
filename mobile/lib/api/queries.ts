import {
  MutationCache,
  QueryCache,
  QueryClient,
  useInfiniteQuery,
  useQuery,
} from '@tanstack/react-query';
import * as Haptics from 'expo-haptics';
import { ApiError, queryString, request } from './client';
import type {
  Blacklist,
  Category,
  Filters,
  HomeFeed,
  HomeSection,
  Page,
  Product,
  ProductDetail,
  Profile,
  Routine,
  Suitability,
} from './types';
import { useSession } from '@/lib/session';
export const notifyError = () => {
  void Haptics.notificationAsync(Haptics.NotificationFeedbackType.Error);
};
export const notifySuccess = () => {
  void Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
};
export const queryClient = new QueryClient({
  queryCache: new QueryCache({ onError: notifyError }),
  mutationCache: new MutationCache({ onError: notifyError }),
  defaultOptions: {
    queries: {
      staleTime: 60000,
      retry: (count, error) =>
        count < 1 && !(error instanceof ApiError && error.status >= 400 && error.status < 500),
    },
    mutations: { retry: false },
  },
});
export const privateKey = (area: string, userId?: string) => [area, userId ?? 'guest'];
export const useUserId = () => useSession((state) => state.session?.user.id);
export function useHome() {
  return useQuery({
    queryKey: ['home'],
    queryFn: ({ signal }) => request<HomeFeed>('/home?limit=10', { signal }),
  });
}
export function useCategories() {
  return useQuery({
    queryKey: ['categories'],
    queryFn: ({ signal }) => request<Category[]>('/categories', { signal }),
  });
}
export function useShelf(section: string) {
  return useInfiniteQuery({
    queryKey: ['shelf', section],
    initialPageParam: null as string | null,
    queryFn: ({ pageParam, signal }) =>
      request<HomeSection>(
        '/home/sections/' + section + queryString({ limit: 20, cursor: pageParam }),
        { signal },
      ),
    getNextPageParam: (page) => page.next_cursor ?? undefined,
  });
}
export function useProducts(filters: Filters, enabled = true) {
  const hasFilters = !!(
    filters.category ||
    filters.band ||
    filters.include?.length ||
    filters.exclude?.length ||
    filters.min_score !== undefined ||
    filters.max_score !== undefined
  );
  return useInfiniteQuery({
    queryKey: ['products', filters],
    enabled,
    initialPageParam: null as string | null,
    queryFn: ({ pageParam, signal }) =>
      request<Page<Product>>(
        '/products/' +
          (hasFilters || !filters.q ? 'filter' : 'search') +
          queryString({ ...filters, limit: 20, cursor: pageParam }),
        { signal },
      ),
    getNextPageParam: (page) => page.next_cursor ?? undefined,
  });
}
export function useProduct(id: string) {
  return useQuery({
    queryKey: ['product', id],
    enabled: !!id,
    queryFn: ({ signal }) =>
      request<ProductDetail>('/products/' + encodeURIComponent(id), { signal }),
  });
}
export function useProfile() {
  const uid = useUserId();
  return useQuery({
    queryKey: privateKey('profile', uid),
    enabled: !!uid,
    queryFn: ({ signal }) => request<Profile>('/profile', { auth: true, signal }),
  });
}
export function useBlacklist() {
  const uid = useUserId();
  return useQuery({
    queryKey: privateKey('blacklist', uid),
    enabled: !!uid,
    queryFn: ({ signal }) => request<Blacklist>('/profile/blacklist', { auth: true, signal }),
  });
}
export function useSuitability(id: string, enabled: boolean) {
  const uid = useUserId();
  return useQuery({
    queryKey: ['suitability', uid, id],
    enabled: !!uid && !!id && enabled,
    queryFn: ({ signal }) =>
      request<Suitability>('/products/' + id + '/suitability', { auth: true, signal }),
  });
}
export function useRoutines() {
  const uid = useUserId();
  return useQuery({
    queryKey: privateKey('routines', uid),
    enabled: !!uid,
    queryFn: ({ signal }) => request<{ routines: Routine[] }>('/routines', { auth: true, signal }),
  });
}
