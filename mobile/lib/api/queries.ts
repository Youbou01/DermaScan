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
  OfferList,
  Page,
  Product,
  ProductDetail,
  ProductCardsPage,
  ProductReviewsPage,
  Profile,
  Routine,
  DermatologistGuidance,
  RoutineShareLinks,
  SavedProductStatus,
  Suitability,
  Slot,
  UserReviewsPage,
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
    filters.max_score !== undefined ||
    filters.sort !== undefined ||
    filters.direction !== undefined
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
export function useOffers(id: string, enabled = true) {
  const uid = useUserId();
  return useQuery({
    queryKey: ['offers', uid, id],
    enabled: !!uid && !!id && enabled,
    queryFn: ({ signal }) =>
      request<OfferList>('/products/' + encodeURIComponent(id) + '/offers', {
        auth: true,
        signal,
      }),
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

export function useSavedProducts() {
  const uid = useUserId();
  return useInfiniteQuery({
    queryKey: privateKey('library-saved', uid),
    enabled: !!uid,
    initialPageParam: null as string | null,
    queryFn: ({ pageParam, signal }) =>
      request<ProductCardsPage>('/library/saved' + queryString({ limit: 50, cursor: pageParam }), {
        auth: true,
        signal,
      }),
    getNextPageParam: (page) => page.next_cursor ?? undefined,
  });
}

export function useRecentlyViewed() {
  const uid = useUserId();
  return useInfiniteQuery({
    queryKey: privateKey('library-recent', uid),
    enabled: !!uid,
    initialPageParam: null as string | null,
    queryFn: ({ pageParam, signal }) =>
      request<ProductCardsPage>(
        '/library/recently-viewed' + queryString({ limit: 20, cursor: pageParam }),
        { auth: true, signal },
      ),
    getNextPageParam: (page) => page.next_cursor ?? undefined,
  });
}

export function useProductReviews(productId: string, enabled = true) {
  return useInfiniteQuery({
    queryKey: ['product-reviews', productId],
    enabled: !!productId && enabled,
    initialPageParam: null as string | null,
    queryFn: ({ pageParam, signal }) =>
      request<ProductReviewsPage>(
        `/products/${encodeURIComponent(productId)}/reviews` +
          queryString({ limit: 20, cursor: pageParam }),
        { signal },
      ),
    getNextPageParam: (page) => page.next_cursor ?? undefined,
  });
}

export function useSavedProduct(productId: string) {
  const uid = useUserId();
  return useQuery({
    queryKey: [...privateKey('library-saved-status', uid), productId],
    enabled: !!uid && !!productId,
    queryFn: ({ signal }) =>
      request<SavedProductStatus>(`/library/saved/${encodeURIComponent(productId)}`, {
        auth: true,
        signal,
      }),
  });
}

export function useRoutineShareLinks(slot: Slot) {
  const uid = useUserId();
  return useQuery({
    queryKey: [...privateKey('routine-shares', uid), slot],
    enabled: !!uid,
    queryFn: ({ signal }) =>
      request<RoutineShareLinks>(`/routines/${slot}/shares`, {
        auth: true,
        signal,
      }),
  });
}

export function useDermatologistGuidance() {
  const uid = useUserId();
  return useQuery({
    queryKey: ['dermatologist-guidance', uid],
    queryFn: ({ signal }) =>
      request<DermatologistGuidance>('/dermatologists/recommendations', {
        auth: !!uid,
        signal,
      }),
  });
}

export function useMyReviews() {
  const uid = useUserId();
  return useInfiniteQuery({
    queryKey: privateKey('my-reviews', uid),
    enabled: !!uid,
    initialPageParam: null as string | null,
    queryFn: ({ pageParam, signal }) =>
      request<UserReviewsPage>(
        '/users/me/reviews' + queryString({ limit: 20, cursor: pageParam }),
        { auth: true, signal },
      ),
    getNextPageParam: (page) => page.next_cursor ?? undefined,
  });
}
