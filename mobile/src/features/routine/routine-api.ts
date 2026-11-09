import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseMutationResult,
  type UseQueryResult,
} from '@tanstack/react-query';
import { env } from '@/config/env';
import { getActiveApiLocale } from '@/api/locale';
import { productCardsFixture } from '@/api/fixtures';
import type { ProductCard } from '@/api/types';

export type RoutineSlot = 'morning' | 'evening';
export type StepType = 'cleanser' | 'toner' | 'serum' | 'moisturizer' | 'sunscreen';
export type SkinTypeOption = 'normal' | 'dry' | 'oily' | 'combination' | 'sensitive';

export interface RoutineStepItem {
  readonly step_order: number;
  readonly step_type: StepType;
  readonly product: ProductCard;
  readonly active_ingredients: readonly string[];
}

export interface RoutineConflict {
  readonly code: string;
  readonly severity: 'high' | 'moderate';
  readonly product_a_id: string;
  readonly product_b_id: string;
  readonly product_a_name: string;
  readonly product_b_name: string;
  readonly ingredient_a: string;
  readonly ingredient_b: string;
  readonly title: string;
  readonly detail: string;
  readonly resolution: string;
}

export interface RoutineData {
  readonly slot: RoutineSlot;
  readonly completed_today: boolean;
  readonly steps: RoutineStepItem[];
  readonly conflicts: RoutineConflict[];
}

export interface RecommendedRoutinesResponse {
  readonly skin_type: SkinTypeOption;
  readonly morning: RoutineStepItem[];
  readonly evening: RoutineStepItem[];
}

export interface CatalogCandidateProduct {
  readonly product: ProductCard;
  readonly defaultStepType: StepType;
  readonly activeIngredients: readonly string[];
}

const RETINOIDS = new Set(['RETINOL', 'RETINAL', 'RETINOIC ACID']);
const AHA_BHA_ACIDS = new Set(['GLYCOLIC ACID', 'SALICYLIC ACID', 'LACTIC ACID']);
const BENZOYL_PEROXIDE = new Set(['BENZOYL PEROXIDE']);
const PURE_VITAMIN_C = new Set(['ASCORBIC ACID', 'L-ASCORBIC ACID']);

const EXTRA_ACTIVE_PRODUCTS: readonly CatalogCandidateProduct[] = [
  {
    product: {
      id: '0194f024-6c67-7e21-9e16-a774b0d53391',
      name: 'Night Renewal Retinol 0.3% Serum',
      brand: 'DermaScan Lab',
      image_url: null,
      score: 64,
      score_band: 'moderate',
      category_slug: 'serum',
    },
    defaultStepType: 'serum',
    activeIngredients: ['RETINOL', 'SQUALANE'],
  },
  {
    product: {
      id: '0194f024-6c67-7e21-9e16-a774b0d53392',
      name: 'Glycolic Acid 7% Resurfacing Toner',
      brand: 'DermaScan Lab',
      image_url: null,
      score: 66,
      score_band: 'moderate',
      category_slug: 'toner',
    },
    defaultStepType: 'toner',
    activeIngredients: ['GLYCOLIC ACID', 'GLYCERIN'],
  },
  {
    product: {
      id: '0194f024-6c67-7e21-9e16-a774b0d53393',
      name: 'Pure Vitamin C 15% Glow Serum',
      brand: 'DermaScan Lab',
      image_url: null,
      score: 78,
      score_band: 'low',
      category_slug: 'serum',
    },
    defaultStepType: 'serum',
    activeIngredients: ['ASCORBIC ACID', 'TOCOPHEROL'],
  },
];

export const ROUTINE_CATALOG_CANDIDATES: readonly CatalogCandidateProduct[] = [
  ...productCardsFixture.slice(0, 5).map((card): CatalogCandidateProduct => {
    const slug = card.category_slug;
    const stepType: StepType =
      slug === 'cleanser'
        ? 'cleanser'
        : slug === 'toner'
          ? 'toner'
          : slug === 'moisturizer'
            ? 'moisturizer'
            : slug === 'sunscreen'
              ? 'sunscreen'
              : 'serum';
    return {
      product: card,
      defaultStepType: stepType,
      activeIngredients: slug === 'serum' ? ['NIACINAMIDE', 'HYALURONIC ACID'] : ['GLYCERIN'],
    };
  }),
  ...EXTRA_ACTIVE_PRODUCTS,
];

export function evaluateRoutineConflicts(steps: readonly RoutineStepItem[]): RoutineConflict[] {
  const locale = getActiveApiLocale();
  const conflicts: RoutineConflict[] = [];

  for (let i = 0; i < steps.length; i += 1) {
    for (let j = i + 1; j < steps.length; j += 1) {
      const stepA = steps[i]!;
      const stepB = steps[j]!;
      const ingsA = stepA.active_ingredients.map((x) => x.toUpperCase());
      const ingsB = stepB.active_ingredients.map((x) => x.toUpperCase());

      const retA = ingsA.find((x) => RETINOIDS.has(x));
      const retB = ingsB.find((x) => RETINOIDS.has(x));
      const acidA = ingsA.find((x) => AHA_BHA_ACIDS.has(x));
      const acidB = ingsB.find((x) => AHA_BHA_ACIDS.has(x));
      const bpoA = ingsA.find((x) => BENZOYL_PEROXIDE.has(x));
      const bpoB = ingsB.find((x) => BENZOYL_PEROXIDE.has(x));
      const vitcA = ingsA.find((x) => PURE_VITAMIN_C.has(x));
      const vitcB = ingsB.find((x) => PURE_VITAMIN_C.has(x));

      if ((retA && acidB) || (acidA && retB)) {
        const ingA = retA ?? acidA!;
        const ingB = acidB ?? retB!;
        conflicts.push({
          code: 'retinoid_x_acid',
          severity: 'high',
          product_a_id: stepA.product.id,
          product_b_id: stepB.product.id,
          product_a_name: stepA.product.name,
          product_b_name: stepB.product.name,
          ingredient_a: ingA,
          ingredient_b: ingB,
          title:
            locale === 'fr'
              ? 'Interaction Rétinoïde + Acide Exfoliant (AHA/BHA)'
              : 'Retinoid + Exfoliating Acid (AHA/BHA) Conflict',
          detail:
            locale === 'fr'
              ? `Combiner ${ingA} et ${ingB} dans la même routine augmente fortement l’irritation de la barrière cutanée.`
              : `Layering ${ingA} and ${ingB} in the same routine significantly increases skin barrier irritation.`,
          resolution:
            locale === 'fr'
              ? 'Utilisez ces produits un soir sur deux ou déplacez le tonique exfoliant dans une autre routine.'
              : 'Use on alternate evenings or move the exfoliating acid to a separate routine.',
        });
      } else if ((retA && bpoB) || (bpoA && retB)) {
        const ingA = retA ?? bpoA!;
        const ingB = bpoB ?? retB!;
        conflicts.push({
          code: 'retinoid_x_bpo',
          severity: 'high',
          product_a_id: stepA.product.id,
          product_b_id: stepB.product.id,
          product_a_name: stepA.product.name,
          product_b_name: stepB.product.name,
          ingredient_a: ingA,
          ingredient_b: ingB,
          title:
            locale === 'fr'
              ? 'Interaction Rétinoïde + Peroxyde de Benzoyle'
              : 'Retinoid + Benzoyl Peroxide Conflict',
          detail:
            locale === 'fr'
              ? 'Le peroxyde de benzoyle peut oxyder le rétinol et accentuer la sécheresse.'
              : 'Benzoyl peroxide can oxidize retinol and compound skin dryness.',
          resolution:
            locale === 'fr'
              ? 'Appliquez le peroxyde de benzoyle le matin et le rétinol le soir.'
              : 'Apply benzoyl peroxide in the morning and retinol in the evening.',
        });
      } else if ((vitcA && (retB || acidB)) || ((retA || acidA) && vitcB)) {
        const ingA = vitcA ?? retA ?? acidA!;
        const ingB = retB ?? acidB ?? vitcB!;
        conflicts.push({
          code: 'vitc_x_active',
          severity: 'moderate',
          product_a_id: stepA.product.id,
          product_b_id: stepB.product.id,
          product_a_name: stepA.product.name,
          product_b_name: stepB.product.name,
          ingredient_a: ingA,
          ingredient_b: ingB,
          title:
            locale === 'fr'
              ? 'Interaction Vitamine C Pure + Actif Intense'
              : 'Pure Vitamin C + Intensive Active Overlap',
          detail:
            locale === 'fr'
              ? `Superposer ${ingA} et ${ingB} peut déséquilibrer le pH et provoquer des picotements.`
              : `Layering ${ingA} with ${ingB} may cause pH mismatch and heightened stinging.`,
          resolution:
            locale === 'fr'
              ? 'Gardez la Vitamine C pour le matin et les rétinoïdes ou acides pour le soir.'
              : 'Keep Vitamin C in your Morning routine and retinoids or acids in your Evening routine.',
        });
      }
    }
  }
  return conflicts;
}

export interface InternalRoutineStore {
  morning: RoutineData;
  evening: RoutineData;
}

function createInitialStore(): InternalRoutineStore {
  const cleanser = ROUTINE_CATALOG_CANDIDATES[1]!;
  const serum = ROUTINE_CATALOG_CANDIDATES[0]!;
  const moisturizer = ROUTINE_CATALOG_CANDIDATES[2]!;
  const sunscreen = ROUTINE_CATALOG_CANDIDATES[3]!;

  const morningSteps: RoutineStepItem[] = [
    {
      step_order: 1,
      step_type: 'cleanser',
      product: cleanser.product,
      active_ingredients: cleanser.activeIngredients,
    },
    {
      step_order: 2,
      step_type: 'serum',
      product: serum.product,
      active_ingredients: serum.activeIngredients,
    },
    {
      step_order: 3,
      step_type: 'moisturizer',
      product: moisturizer.product,
      active_ingredients: moisturizer.activeIngredients,
    },
    {
      step_order: 4,
      step_type: 'sunscreen',
      product: sunscreen.product,
      active_ingredients: sunscreen.activeIngredients,
    },
  ];

  const eveningSteps: RoutineStepItem[] = [
    {
      step_order: 1,
      step_type: 'cleanser',
      product: cleanser.product,
      active_ingredients: cleanser.activeIngredients,
    },
    {
      step_order: 2,
      step_type: 'moisturizer',
      product: moisturizer.product,
      active_ingredients: moisturizer.activeIngredients,
    },
  ];

  return {
    morning: {
      slot: 'morning',
      completed_today: false,
      steps: morningSteps,
      conflicts: evaluateRoutineConflicts(morningSteps),
    },
    evening: {
      slot: 'evening',
      completed_today: false,
      steps: eveningSteps,
      conflicts: evaluateRoutineConflicts(eveningSteps),
    },
  };
}

let routineStore: InternalRoutineStore = createInitialStore();

export function resetMockRoutineStore(): void {
  routineStore = createInitialStore();
}

export function buildRecommendationsForSkinType(
  skinType: SkinTypeOption,
): RecommendedRoutinesResponse {
  const cleanser = ROUTINE_CATALOG_CANDIDATES[1]!;
  const toner = ROUTINE_CATALOG_CANDIDATES[4]!;
  const hydratingSerum = ROUTINE_CATALOG_CANDIDATES[0]!;
  const vitCSerum = EXTRA_ACTIVE_PRODUCTS[2]!;
  const moisturizer = ROUTINE_CATALOG_CANDIDATES[2]!;
  const sunscreen = ROUTINE_CATALOG_CANDIDATES[3]!;
  const retinolSerum = EXTRA_ACTIVE_PRODUCTS[0]!;

  const morningSerum = skinType === 'sensitive' ? hydratingSerum : vitCSerum;
  const eveningTreatment =
    skinType === 'sensitive' || skinType === 'dry' ? hydratingSerum : retinolSerum;

  const morning: RoutineStepItem[] = [
    {
      step_order: 1,
      step_type: 'cleanser',
      product: cleanser.product,
      active_ingredients: cleanser.activeIngredients,
    },
    {
      step_order: 2,
      step_type: 'serum',
      product: morningSerum.product,
      active_ingredients: morningSerum.activeIngredients,
    },
    {
      step_order: 3,
      step_type: 'moisturizer',
      product: moisturizer.product,
      active_ingredients: moisturizer.activeIngredients,
    },
    {
      step_order: 4,
      step_type: 'sunscreen',
      product: sunscreen.product,
      active_ingredients: sunscreen.activeIngredients,
    },
  ];

  const evening: RoutineStepItem[] = [
    {
      step_order: 1,
      step_type: 'cleanser',
      product: cleanser.product,
      active_ingredients: cleanser.activeIngredients,
    },
    {
      step_order: 2,
      step_type: 'toner',
      product: toner.product,
      active_ingredients: toner.activeIngredients,
    },
    {
      step_order: 3,
      step_type: 'serum',
      product: eveningTreatment.product,
      active_ingredients: eveningTreatment.activeIngredients,
    },
    {
      step_order: 4,
      step_type: 'moisturizer',
      product: moisturizer.product,
      active_ingredients: moisturizer.activeIngredients,
    },
  ];

  return {
    skin_type: skinType,
    morning,
    evening,
  };
}

export function useRoutinesQuery(): UseQueryResult<InternalRoutineStore, Error> {
  return useQuery({
    queryKey: ['routines'],
    queryFn: async (): Promise<InternalRoutineStore> => {
      if (!env.useMocks) {
        try {
          const res = await fetch(`${env.apiUrl}/api/v1/routines`, {
            headers: { 'Accept-Language': getActiveApiLocale() },
          });
          if (res.ok) {
            const data = (await res.json()) as { routines?: RoutineData[] };
            const am = data.routines?.find((r) => r.slot === 'morning');
            const pm = data.routines?.find((r) => r.slot === 'evening');
            if (am && pm) {
              routineStore = { morning: am, evening: pm };
              return routineStore;
            }
          }
        } catch {
          // Fall back to local routine state when offline
        }
      }
      return {
        morning: {
          ...routineStore.morning,
          conflicts: evaluateRoutineConflicts(routineStore.morning.steps),
        },
        evening: {
          ...routineStore.evening,
          conflicts: evaluateRoutineConflicts(routineStore.evening.steps),
        },
      };
    },
  });
}

export function useUpdateRoutineMutation(): UseMutationResult<
  RoutineData,
  Error,
  { slot: RoutineSlot; steps: RoutineStepItem[] }
> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ slot, steps }): Promise<RoutineData> => {
      const normalizedSteps = steps.map((step, index) => ({
        ...step,
        step_order: index + 1,
      }));
      const conflicts = evaluateRoutineConflicts(normalizedSteps);
      const localUpdated: RoutineData = {
        ...routineStore[slot],
        steps: normalizedSteps,
        conflicts,
      };

      if (!env.useMocks) {
        try {
          const res = await fetch(`${env.apiUrl}/api/v1/routines/${slot}`, {
            method: 'PUT',
            headers: {
              'Content-Type': 'application/json',
              'Accept-Language': getActiveApiLocale(),
            },
            body: JSON.stringify({ steps: normalizedSteps }),
          });
          if (res.ok) {
            const serverData = (await res.json()) as RoutineData;
            routineStore = {
              ...routineStore,
              [slot]: serverData,
            };
            return serverData;
          }
          console.warn(
            `PUT /api/v1/routines/${slot} failed with status ${res.status}; falling back to local routine state.`,
          );
        } catch {
          console.warn(
            `PUT /api/v1/routines/${slot} network failure; falling back to local routine state.`,
          );
        }
      }

      routineStore = {
        ...routineStore,
        [slot]: localUpdated,
      };
      return localUpdated;
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['routines'] });
    },
  });
}

export function useToggleRoutineCompletionMutation(): UseMutationResult<
  RoutineData,
  Error,
  RoutineSlot
> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (slot: RoutineSlot): Promise<RoutineData> => {
      const current = routineStore[slot];
      const localUpdated: RoutineData = {
        ...current,
        completed_today: !current.completed_today,
      };

      if (!env.useMocks) {
        try {
          const res = await fetch(`${env.apiUrl}/api/v1/routines/${slot}/complete`, {
            method: 'POST',
            headers: {
              'Accept-Language': getActiveApiLocale(),
            },
          });
          if (res.ok) {
            const serverData = (await res.json()) as RoutineData;
            routineStore = {
              ...routineStore,
              [slot]: serverData,
            };
            return serverData;
          }
          console.warn(
            `POST /api/v1/routines/${slot}/complete failed with status ${res.status}; falling back to local routine state.`,
          );
        } catch {
          console.warn(
            `POST /api/v1/routines/${slot}/complete network failure; falling back to local routine state.`,
          );
        }
      }

      routineStore = {
        ...routineStore,
        [slot]: localUpdated,
      };
      return localUpdated;
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['routines'] });
    },
  });
}

export function checkCandidateConflict(
  candidate: CatalogCandidateProduct,
  currentSteps: readonly RoutineStepItem[],
): RoutineConflict | null {
  const hypotheticalStep: RoutineStepItem = {
    step_order: currentSteps.length + 1,
    step_type: candidate.defaultStepType,
    product: candidate.product,
    active_ingredients: candidate.activeIngredients,
  };
  const allConflicts = evaluateRoutineConflicts([...currentSteps, hypotheticalStep]);
  return (
    allConflicts.find(
      (conflict) =>
        conflict.product_a_id === candidate.product.id ||
        conflict.product_b_id === candidate.product.id,
    ) ?? null
  );
}

export function useRoutineRecommendationsQuery(
  skinType: SkinTypeOption,
): UseQueryResult<RecommendedRoutinesResponse, Error> {
  return useQuery({
    queryKey: ['routine-recommendations', skinType],
    queryFn: async (): Promise<RecommendedRoutinesResponse> =>
      buildRecommendationsForSkinType(skinType),
  });
}
