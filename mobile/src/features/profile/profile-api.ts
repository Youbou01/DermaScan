import {
  useMutation,
  useQueries,
  useQuery,
  useQueryClient,
  type UseMutationResult,
  type UseQueryResult,
} from '@tanstack/react-query';
import { buildAuthHeaders, getActiveAccessToken } from '@/api/auth-token';
import { apiClient } from '@/api/client';
import { KNOWN_PROFILE_INGREDIENTS, productCardsFixture, productFixture } from '@/api/fixtures';
import { getActiveApiLocale } from '@/api/locale';
import type {
  BlacklistOut,
  HealthCondition,
  ProductIngredient,
  ProfileOut,
  ProfileUpdateIn,
  RiskAlert,
  SkinType,
  SuitabilityResult,
  Verdict,
} from '@/api/types';
import { env } from '@/config/env';

export class ProfileAuthRequiredError extends Error {
  constructor() {
    super('Authentication required');
    this.name = 'ProfileAuthRequiredError';
  }
}

interface InternalProfileState {
  skin_type: SkinType | null;
  is_pregnant_or_nursing: boolean;
  health_conditions: HealthCondition[];
  allergy_ingredient_ids: string[];
  blacklisted_product_ids: string[];
  blacklisted_ingredient_ids: string[];
}

function createInitialProfileState(): InternalProfileState {
  return {
    skin_type: null,
    is_pregnant_or_nursing: false,
    health_conditions: [],
    allergy_ingredient_ids: [],
    blacklisted_product_ids: [],
    blacklisted_ingredient_ids: [],
  };
}

let profileStore: InternalProfileState = createInitialProfileState();

export function resetMockProfileStore(): void {
  profileStore = createInitialProfileState();
}

export function getLocalProfileSnapshot(): InternalProfileState {
  return profileStore;
}

const PREGNANCY_CONTRAINDICATED_NAMES = new Set([
  'RETINOL',
  'RETINAL',
  'RETINOIC ACID',
  'RETINYL PALMITATE',
  'HYDROXYPINACOLONE RETINOATE',
  'HYDROQUINONE',
  'SALICYLIC ACID',
  'BENZOYL PEROXIDE',
]);

const DRYING_NAMES = new Set(['ALCOHOL DENAT.', 'SODIUM LAURYL SULFATE']);
const OCCLUSIVE_NAMES = new Set(['PETROLATUM', 'PARAFFINUM LIQUIDUM', 'LANOLIN']);

export function evaluateLocalSuitability(
  productId: string,
  ingredients: readonly ProductIngredient[],
  state: InternalProfileState = profileStore,
): SuitabilityResult {
  const locale = getActiveApiLocale();
  const isFr = locale === 'fr';
  const alerts: RiskAlert[] = [];

  const isSensitive =
    state.skin_type === 'sensitive' ||
    state.health_conditions.includes('eczema') ||
    state.health_conditions.includes('rosacea');
  const isDryOrSensitive = state.skin_type === 'dry' || state.skin_type === 'sensitive';
  const isOilyOrAcne = state.skin_type === 'oily' || state.health_conditions.includes('acne_prone');

  const allergyInciSet = new Set(
    KNOWN_PROFILE_INGREDIENTS.filter((k) => state.allergy_ingredient_ids.includes(k.id)).map((k) =>
      k.inci_name.toUpperCase(),
    ),
  );
  const blacklistedInciSet = new Set(
    KNOWN_PROFILE_INGREDIENTS.filter((k) => state.blacklisted_ingredient_ids.includes(k.id)).map(
      (k) => k.inci_name.toUpperCase(),
    ),
  );

  for (const item of ingredients) {
    const candidateName = (item.inci_name ?? item.name).trim().toUpperCase();
    const itemIngId = item.ingredient_id ?? null;

    if (state.is_pregnant_or_nursing && PREGNANCY_CONTRAINDICATED_NAMES.has(candidateName)) {
      alerts.push({
        code: 'pregnancy_contraindication',
        severity: 'high',
        ingredient_name: candidateName,
        title: isFr ? 'Déconseillé pendant la grossesse' : 'Not recommended during pregnancy',
        detail: isFr
          ? `Contient ${candidateName}, contre-indiqué pendant la grossesse et l'allaitement.`
          : `Contains ${candidateName}, which is contraindicated during pregnancy and nursing.`,
      });
    }

    if (
      (itemIngId && state.allergy_ingredient_ids.includes(itemIngId)) ||
      allergyInciSet.has(candidateName) ||
      (isSensitive && candidateName === 'PARFUM')
    ) {
      alerts.push({
        code: 'allergy_match',
        severity: 'high',
        ingredient_name: candidateName,
        title: isFr
          ? "Correspond à votre profil d'allergie ou de sensibilité"
          : 'Matches your allergy or sensitivity profile',
        detail: isFr
          ? `Contient ${candidateName}, qui correspond à vos allergies ou sensibilités déclarées.`
          : `Contains ${candidateName}, which matches your declared allergies or sensitivities.`,
      });
    }

    if (
      (itemIngId && state.blacklisted_ingredient_ids.includes(itemIngId)) ||
      blacklistedInciSet.has(candidateName)
    ) {
      alerts.push({
        code: 'blacklisted',
        severity: 'high',
        ingredient_name: candidateName,
        title: isFr ? 'Dans votre liste noire' : 'On your blacklist',
        detail: isFr
          ? `Contient ${candidateName}, un ingrédient de votre liste noire.`
          : `Contains ${candidateName}, an ingredient you blacklisted.`,
      });
    }

    if (isDryOrSensitive && DRYING_NAMES.has(candidateName)) {
      alerts.push({
        code: 'skin_type_mismatch',
        severity: 'medium',
        ingredient_name: candidateName,
        title: isFr ? 'Peut ne pas convenir à votre type de peau' : 'May not suit your skin type',
        detail: isFr
          ? `Contient ${candidateName}, qui peut dessécher les peaux sèches ou sensibles.`
          : `Contains ${candidateName}, which can be drying for dry or sensitive skin.`,
      });
    }

    if (isOilyOrAcne && OCCLUSIVE_NAMES.has(candidateName)) {
      alerts.push({
        code: 'skin_type_mismatch',
        severity: 'medium',
        ingredient_name: candidateName,
        title: isFr ? 'Peut ne pas convenir à votre type de peau' : 'May not suit your skin type',
        detail: isFr
          ? `Contient ${candidateName}, un occlusif riche pour les peaux grasses ou à tendance acnéique.`
          : `Contains ${candidateName}, a heavy occlusive for oily or acne-prone skin.`,
      });
    }
  }

  alerts.sort((a, b) => (a.severity === b.severity ? 0 : a.severity === 'high' ? -1 : 1));
  const productBlacklisted = state.blacklisted_product_ids.includes(productId);
  const isBlacklisted = productBlacklisted || alerts.some((alert) => alert.code === 'blacklisted');
  const hasHighAlert = alerts.some((alert) => alert.severity === 'high');

  const verdict: Verdict =
    isBlacklisted || hasHighAlert ? 'avoid' : alerts.length > 0 ? 'caution' : 'suitable';

  return {
    product_id: productId,
    suits_profile: verdict === 'suitable',
    verdict,
    has_risk_alert: alerts.length > 0 || isBlacklisted,
    is_blacklisted: isBlacklisted,
    alerts,
  };
}

export function useProfileQuery(): UseQueryResult<ProfileOut, Error> {
  const token = getActiveAccessToken();
  return useQuery({
    queryKey: ['profile', token],
    queryFn: async (): Promise<ProfileOut> => {
      if (!env.useMocks && token) {
        try {
          const response = await fetch(`${env.apiUrl}/api/v1/profile`, {
            headers: buildAuthHeaders({ 'Accept-Language': getActiveApiLocale() }),
          });
          if (response.ok) {
            const serverProfile = (await response.json()) as ProfileOut;
            profileStore = {
              ...profileStore,
              skin_type: serverProfile.skin_type,
              is_pregnant_or_nursing: serverProfile.is_pregnant_or_nursing,
              health_conditions: serverProfile.health_conditions,
              allergy_ingredient_ids: serverProfile.allergy_ingredient_ids,
              blacklisted_product_ids: serverProfile.blacklisted_product_ids,
            };
            return serverProfile;
          }
        } catch {
          // Fall back to local profile state
        }
      }
      return {
        user_id: '0194f024-6c67-7e21-9e16-a774b0d53999',
        skin_type: profileStore.skin_type,
        is_pregnant_or_nursing: profileStore.is_pregnant_or_nursing,
        health_conditions: profileStore.health_conditions,
        allergy_ingredient_ids: profileStore.allergy_ingredient_ids,
        blacklisted_product_ids: profileStore.blacklisted_product_ids,
      };
    },
  });
}

export function useUpdateProfileMutation(): UseMutationResult<ProfileOut, Error, ProfileUpdateIn> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: ProfileUpdateIn): Promise<ProfileOut> => {
      if (!env.useMocks) {
        if (!getActiveAccessToken()) {
          throw new ProfileAuthRequiredError();
        }
        const response = await fetch(`${env.apiUrl}/api/v1/profile`, {
          method: 'PUT',
          headers: buildAuthHeaders({
            'Content-Type': 'application/json',
            'Accept-Language': getActiveApiLocale(),
          }),
          body: JSON.stringify(payload),
        });
        if (response.status === 401) {
          throw new ProfileAuthRequiredError();
        }
        if (response.ok) {
          const updated = (await response.json()) as ProfileOut;
          profileStore = {
            ...profileStore,
            skin_type: updated.skin_type,
            is_pregnant_or_nursing: updated.is_pregnant_or_nursing,
            health_conditions: updated.health_conditions,
            allergy_ingredient_ids: updated.allergy_ingredient_ids,
            blacklisted_product_ids: updated.blacklisted_product_ids,
          };
          return updated;
        }
      }

      profileStore = {
        ...profileStore,
        skin_type: payload.skin_type ?? null,
        is_pregnant_or_nursing: payload.is_pregnant_or_nursing ?? false,
        health_conditions: payload.health_conditions ?? [],
        allergy_ingredient_ids: payload.allergy_ingredient_ids ?? [],
      };

      return {
        user_id: '0194f024-6c67-7e21-9e16-a774b0d53999',
        skin_type: profileStore.skin_type,
        is_pregnant_or_nursing: profileStore.is_pregnant_or_nursing,
        health_conditions: profileStore.health_conditions,
        allergy_ingredient_ids: profileStore.allergy_ingredient_ids,
        blacklisted_product_ids: profileStore.blacklisted_product_ids,
      };
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['profile'] });
      await queryClient.invalidateQueries({ queryKey: ['suitability'] });
    },
  });
}

export function useBlacklistQuery(): UseQueryResult<BlacklistOut, Error> {
  const token = getActiveAccessToken();
  return useQuery({
    queryKey: ['blacklist', token],
    queryFn: async (): Promise<BlacklistOut> => {
      if (!env.useMocks && token) {
        try {
          const response = await fetch(`${env.apiUrl}/api/v1/profile/blacklist`, {
            headers: buildAuthHeaders({ 'Accept-Language': getActiveApiLocale() }),
          });
          if (response.ok) {
            const data = (await response.json()) as BlacklistOut;
            profileStore = {
              ...profileStore,
              blacklisted_product_ids: data.product_ids,
              blacklisted_ingredient_ids: data.ingredient_ids,
            };
            return data;
          }
        } catch {
          // Fall back to local state
        }
      }
      return {
        product_ids: profileStore.blacklisted_product_ids,
        ingredient_ids: profileStore.blacklisted_ingredient_ids,
      };
    },
  });
}

export function useToggleBlacklistProductMutation(): UseMutationResult<
  BlacklistOut,
  Error,
  string
> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (productId: string): Promise<BlacklistOut> => {
      const exists = profileStore.blacklisted_product_ids.includes(productId);

      if (!env.useMocks) {
        if (!getActiveAccessToken()) {
          throw new ProfileAuthRequiredError();
        }
        const response = await fetch(
          `${env.apiUrl}/api/v1/profile/blacklist/products/${productId}`,
          {
            method: exists ? 'DELETE' : 'POST',
            headers: buildAuthHeaders({ 'Accept-Language': getActiveApiLocale() }),
          },
        );
        if (response.status === 401) {
          throw new ProfileAuthRequiredError();
        }
      }

      const nextProducts = exists
        ? profileStore.blacklisted_product_ids.filter((id) => id !== productId)
        : [...profileStore.blacklisted_product_ids, productId];

      profileStore = {
        ...profileStore,
        blacklisted_product_ids: nextProducts,
      };

      return {
        product_ids: profileStore.blacklisted_product_ids,
        ingredient_ids: profileStore.blacklisted_ingredient_ids,
      };
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['blacklist'] });
      await queryClient.invalidateQueries({ queryKey: ['profile'] });
      await queryClient.invalidateQueries({ queryKey: ['suitability'] });
    },
  });
}

export function useToggleBlacklistIngredientMutation(): UseMutationResult<
  BlacklistOut,
  Error,
  string
> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (ingredientId: string): Promise<BlacklistOut> => {
      const exists = profileStore.blacklisted_ingredient_ids.includes(ingredientId);

      if (!env.useMocks) {
        if (!getActiveAccessToken()) {
          throw new ProfileAuthRequiredError();
        }
        const response = await fetch(
          `${env.apiUrl}/api/v1/profile/blacklist/ingredients/${ingredientId}`,
          {
            method: exists ? 'DELETE' : 'POST',
            headers: buildAuthHeaders({ 'Accept-Language': getActiveApiLocale() }),
          },
        );
        if (response.status === 401) {
          throw new ProfileAuthRequiredError();
        }
      }

      const nextIngredients = exists
        ? profileStore.blacklisted_ingredient_ids.filter((id) => id !== ingredientId)
        : [...profileStore.blacklisted_ingredient_ids, ingredientId];

      profileStore = {
        ...profileStore,
        blacklisted_ingredient_ids: nextIngredients,
      };

      return {
        product_ids: profileStore.blacklisted_product_ids,
        ingredient_ids: profileStore.blacklisted_ingredient_ids,
      };
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['blacklist'] });
      await queryClient.invalidateQueries({ queryKey: ['suitability'] });
    },
  });
}

export function useBlacklistedProductsDetails(
  productIds: readonly string[],
): Record<string, { name: string; brand: string | null }> {
  const results = useQueries({
    queries: productIds.map((pid) => ({
      queryKey: ['product', pid],
      queryFn: async () => {
        const res = await apiClient.GET('/api/v1/products/{product_id}', {
          params: { path: { product_id: pid } },
        });
        if (res.response.ok && res.data) {
          return res.data;
        }
        const fallback = productCardsFixture.find((c) => c.id === pid);
        if (fallback) {
          return {
            ...productFixture,
            id: fallback.id,
            name: fallback.name,
            brand: fallback.brand,
          };
        }
        throw new Error('Product not found');
      },
      staleTime: 5 * 60_000,
    })),
  });

  const map: Record<string, { name: string; brand: string | null }> = {};
  productIds.forEach((pid, idx) => {
    const data = results[idx]?.data;
    if (data) {
      map[pid] = { name: data.name, brand: data.brand };
    } else {
      const matchedCard = productCardsFixture.find((p) => p.id === pid);
      if (matchedCard) {
        map[pid] = { name: matchedCard.name, brand: matchedCard.brand };
      }
    }
  });
  return map;
}

export function useProductSuitabilityQuery(
  productId: string | undefined,
  ingredients: readonly ProductIngredient[] = [],
): UseQueryResult<SuitabilityResult, Error> {
  const token = getActiveAccessToken();
  return useQuery({
    queryKey: ['suitability', productId, ingredients.length, token],
    enabled: Boolean(productId),
    queryFn: async (): Promise<SuitabilityResult> => {
      if (!productId) {
        throw new Error('Product ID is required');
      }
      if (!env.useMocks && token) {
        try {
          const response = await fetch(`${env.apiUrl}/api/v1/products/${productId}/suitability`, {
            headers: buildAuthHeaders({ 'Accept-Language': getActiveApiLocale() }),
          });
          if (response.ok) {
            return (await response.json()) as SuitabilityResult;
          }
        } catch {
          // Fall back to deterministic local suitability evaluation
        }
      }
      return evaluateLocalSuitability(productId, ingredients, profileStore);
    },
  });
}
