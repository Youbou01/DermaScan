# System Role & Execution Mandate (For Coding Agent: Gemini 3.8 Flash)

You are an autonomous **Principal Full-Stack Engineer (FastAPI Backend + React Native / Expo SDK 58 Mobile)** working in the **DermaScan** repository.

Live testing on Expo and inspection of the Expo CLI logs (`expolog.txt`) identified **5 specific issues and feature requirements** that must be implemented and verified end-to-end:

1. **Expo CLI Error — `Uncaught (in promise) ProfileAuthRequiredError: Authentication required` (`profile-api.ts:344` & `product-detail-screen.tsx`):**
   * When a user is not signed in (or has an expired token in storage) and taps the product/ingredient blacklist button on `ProductDetailScreen` or `ProfileScreen`, `toggleBlacklistProduct.mutateAsync` throws `ProfileAuthRequiredError` without a `try/catch` handler in `ProductDetailScreen.tsx`, causing an unhandled promise rejection in Expo.
   * Additionally, when `useProfileQuery()` or `useBlacklistQuery()` receives `401 Unauthorized` from the backend (due to an expired JWT), the stale token remains in `auth-token.ts`, causing subsequent mutations to think a token is present and fail with `401`.
2. **Expo CLI Warnings — Routine `POST /complete` (`404`) and `PUT /routines/{slot}` (`422`):**
   * `PUT /api/v1/routines/{slot}` in `mobile/src/features/routine/routine-api.ts` sends `RoutineStepItem` objects (`{ step_order, step_type, product, active_ingredients }`), whereas the backend `RoutineStepIn` schema (`extra="forbid"`) strictly requires `{ step_order, step_type, product_id, notes? }`, causing FastAPI to reject every `PUT` with **HTTP 422**.
   * When a signed-in user has no routines saved in PostgreSQL yet, `GET /api/v1/routines` returns `{ routines: [] }`. `useRoutinesQuery` in `routine-api.ts` checks `if (am && pm)` and falls back to `createInitialStore()` containing **hardcoded mock product UUIDs** (`0194f024-...`) that do not exist in PostgreSQL, causing `PUT /api/v1/routines/{slot}` and `POST /api/v1/routines/{slot}/complete` to fail with `404` / `422`.
   * On the backend, `RoutineService.toggle_completion` raises `404 RoutineNotFoundError` if the routine row for `slot` has not been created yet instead of using `get_or_create_for_user_slot`.
3. **Profile State Does Not Reset on Sign-Out (`ProfileScreen.tsx` & `profile-api.ts`):**
   * When signing out, the module-level `profileStore` in `profile-api.ts` is never reset (`resetMockProfileStore()`), and `ProfileScreenContent` keeps its `key={profileQuery.data.user_id}` because the unauthenticated fallback always returns the same static `user_id` (`0194f024-6c67-7e21-9e16-a774b0d53999`). As a result, `skinType`, `isPregnant`, `conditions`, `allergies`, and `blacklist` remain visibly selected after logging out.
4. **Multi-Ingredient Include & Exclude Filter UI + Backend Keyword Resolution (`ProductCatalogScreen.tsx`, `search-api.ts`, `search_service.py`):**
   * The backend `GET /api/v1/products/filter` endpoint accepts multiple `include` and `exclude` ingredient parameters, but `ProductCatalogScreen.tsx` only has a single text input per field without a way to add multiple ingredients as chips.
   * We need an **"Add" button** directly under both the "Must include ingredient (INCI)" and "Exclude ingredient (INCI)" inputs so users can add as many included and excluded ingredients as they want, view them as removable chips, and filter products containing **all** included ingredients and **none** of the excluded ingredients.

---

## Strict Operating Rules (Non-Negotiable)

1. **Execute Sequentially Without Improvisation:** Execute **Micro-Steps 1 through 8** in exact order. Do not skip any step.
2. **Preserve All Existing Passing Tests:** All existing Backend tests (`uv run pytest`) and Mobile tests (`npm test`) **MUST** remain 100% green, and new tests must be added for the new behavior.
3. **Code Quality & Linter Rules:**
   * **Backend:** Strict type annotations (`ruff` `ANN` + `mypy --strict`), line length <= 100, `uv run lint-imports` contracts respected.
   * **Mobile:** No `any`, explicit return types on all functions and components (`: ReactElement`, `: ReactElement | null`, `: void`, `: Promise<void>`), inline type imports, no floating promises, no `console.log`, and never use `accessibilityRole="status"`.
   * **Product Wording Rule:** Never use the words `safe`, `unsafe`, `toxic`, `harmful`, or `dangerous` in any UI text, translation string, or code comment.

---

## Micro-Step 1: Fix Backend Routine Completion on Uninitialized Slot & Multi-Ingredient Filter Matching

### Goal
1. In `backend/src/app/modules/routines/service.py`, update `toggle_completion` to use `get_or_create_for_user_slot(user_id, slot)` so marking a routine completed never fails with `404` when the user has not saved steps yet.
2. In `backend/src/app/modules/ingredients/repository.py` and `service.py`, add `resolve_filter_ingredient_ids(term)` so multi-ingredient `include` and `exclude` filters match exact aliases, prefix/substring INCI names, and trigram similarity.

### Action 1.1 — Update `toggle_completion` in `backend/src/app/modules/routines/service.py`
In `backend/src/app/modules/routines/service.py`, replace `toggle_completion` (around lines 81–87) with:

```python
    async def toggle_completion(
        self, user_id: uuid.UUID, slot: RoutineSlot, locale: str
    ) -> RoutineDataOut:
        routine = await self._repository.get_or_create_for_user_slot(user_id, slot)
        completed = await self._repository.toggle_completion(routine.id, _today())
        return await self._to_out(routine, locale, completed_today=completed)
```
*(Note: If `RoutineNotFoundError` in `service.py` is no longer used, remove it from the imports in `backend/src/app/modules/routines/service.py` so `ruff` does not flag an unused import).*

### Action 1.2 — Add `search_ids_by_keyword` to `backend/src/app/modules/ingredients/repository.py`
In `backend/src/app/modules/ingredients/repository.py`, add the following method to `IngredientRepository`:

```python
    async def search_ids_by_keyword(self, normalized: str, *, limit: int = 25) -> list[uuid.UUID]:
        """Find ingredient IDs whose normalized alias or INCI name matches or contains `normalized`."""
        if not normalized:
            return []
        stmt = (
            select(Ingredient.id)
            .outerjoin(IngredientAlias, IngredientAlias.ingredient_id == Ingredient.id)
            .where(
                (IngredientAlias.normalized_alias == normalized)
                | IngredientAlias.normalized_alias.startswith(normalized, autoescape=True)
                | IngredientAlias.normalized_alias.contains(normalized, autoescape=True)
                | func.lower(Ingredient.inci_name).contains(normalized, autoescape=True)
            )
            .distinct()
            .limit(limit)
        )
        result = await self._session.scalars(stmt)
        return list(result.all())
```

### Action 1.3 — Add `resolve_filter_ingredient_ids` to `backend/src/app/modules/ingredients/service.py`
In `backend/src/app/modules/ingredients/service.py`, add the following method to `IngredientService`:

```python
    async def resolve_filter_ingredient_ids(self, term: str) -> list[uuid.UUID]:
        """Resolve a user filter term to matching ingredient IDs (exact, substring, or trigram)."""
        key = normalize(term)
        if not key:
            return []
        exact = await self.match([term])
        ids: list[uuid.UUID] = []
        if exact and exact[0].ingredient_id is not None:
            ids.append(exact[0].ingredient_id)
        keyword_ids = await self._repository.search_ids_by_keyword(key, limit=25)
        for kid in keyword_ids:
            if kid not in ids:
                ids.append(kid)
        if not ids:
            suggestions = await self.suggest(term, limit=5, min_similarity=0.5)
            for s in suggestions:
                if s.ingredient_id not in ids:
                    ids.append(s.ingredient_id)
        return ids
```

### Action 1.4 — Update `_resolve_ingredient_groups` in `backend/src/app/modules/catalog/search_service.py`
In `backend/src/app/modules/catalog/search_service.py`, replace `_resolve_ingredient_groups` with:

```python
async def _resolve_ingredient_groups(
    session: AsyncSession, raw_names: list[str]
) -> tuple[list[list[uuid.UUID]], list[str]]:
    """Resolve each ingredient filter term to its candidate ingredient IDs."""
    expanded: list[str] = []
    for raw in raw_names:
        for part in raw.split(","):
            cleaned = part.strip()
            if cleaned:
                expanded.append(cleaned)

    if not expanded:
        return [], []

    ing_service = IngredientService(session)
    groups: list[list[uuid.UUID]] = []
    unmatched: list[str] = []

    for term in expanded:
        matched_ids = await ing_service.resolve_filter_ingredient_ids(term)
        if matched_ids:
            groups.append(matched_ids)
        else:
            unmatched.append(term)

    return groups, unmatched
```

---

## Micro-Step 2: Add Bilingual i18n Keys for Multi-Ingredient Filter Buttons (`en.json` & `fr.json`)

### Goal
Add translation keys for the "Add" buttons and empty/chip removal labels under the Include and Exclude ingredient filters in `mobile/src/i18n/en.json` and `mobile/src/i18n/fr.json`.

### Action 2.1 — Update `"search"` in `mobile/src/i18n/en.json`
In `mobile/src/i18n/en.json`, inside the `"search"` object, add these 4 keys right after `"exclude_placeholder"`:

```json
    "add_include_button": "+ Add included ingredient",
    "add_exclude_button": "+ Add excluded ingredient",
    "remove_include_chip": "Remove included ingredient {{name}}",
    "remove_exclude_chip": "Remove excluded ingredient {{name}}",
```

### Action 2.2 — Update `"search"` in `mobile/src/i18n/fr.json`
In `mobile/src/i18n/fr.json`, inside the `"search"` object, add the exact same 4 keys with French translations right after `"exclude_placeholder"`:

```json
    "add_include_button": "+ Ajouter l’ingrédient requis",
    "add_exclude_button": "+ Ajouter l’ingrédient à exclure",
    "remove_include_chip": "Retirer l’ingrédient requis {{name}}",
    "remove_exclude_chip": "Retirer l’ingrédient exclu {{name}}",
```

---

## Micro-Step 3: Fix Profile Reset on Sign-Out & Expired Token Cleanup (`profile-api.ts` & `AuthContext.tsx`)

### Goal
1. Ensure signing out (`signOut()` in `AuthContext.tsx`) immediately calls `resetMockProfileStore()` and `resetMockRoutineStore()`, and resets all cached profile/blacklist/routine data so `ProfileScreen` immediately clears skin type, pregnancy status, conditions, allergies, and blacklisted items.
2. Ensure `useProfileQuery()` and `useBlacklistQuery()` use `'guest'` vs `token` in their `user_id` (`user_id: token ? 'authenticated-user' : 'guest-user'`) so `ProfileScreenContent` (`key={profileQuery.data.user_id}`) remounts with clean initial state when signing out.
3. If the backend returns `401` on `GET /api/v1/profile` or `GET /api/v1/profile/blacklist` (expired token), automatically clear the expired token via `setActiveAccessToken(null)` and `resetMockProfileStore()`.

### Action 3.1 — Update `mobile/src/features/profile/profile-api.ts`
In `mobile/src/features/profile/profile-api.ts`, update `useProfileQuery` and `useBlacklistQuery` to clear expired tokens on `401` and return a distinct `'guest-user'` `user_id` when signed out:

```typescript
export function useProfileQuery(): UseQueryResult<ProfileOut, Error> {
  const token = getActiveAccessToken();
  return useQuery({
    queryKey: ['profile', token ?? 'guest'],
    queryFn: async (): Promise<ProfileOut> => {
      if (!env.useMocks && token) {
        try {
          const response = await fetch(`${env.apiUrl}/api/v1/profile`, {
            headers: buildAuthHeaders({ 'Accept-Language': getActiveApiLocale() }),
          });
          if (response.status === 401) {
            setActiveAccessToken(null);
            resetMockProfileStore();
          } else if (response.ok) {
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
        user_id: token ? '0194f024-6c67-7e21-9e16-a774b0d53999' : 'guest-user',
        skin_type: profileStore.skin_type,
        is_pregnant_or_nursing: profileStore.is_pregnant_or_nursing,
        health_conditions: profileStore.health_conditions,
        allergy_ingredient_ids: profileStore.allergy_ingredient_ids,
        blacklisted_product_ids: profileStore.blacklisted_product_ids,
      };
    },
  });
}
```
And in `useBlacklistQuery`:
```typescript
export function useBlacklistQuery(): UseQueryResult<BlacklistOut, Error> {
  const token = getActiveAccessToken();
  return useQuery({
    queryKey: ['blacklist', token ?? 'guest'],
    queryFn: async (): Promise<BlacklistOut> => {
      if (!env.useMocks && token) {
        try {
          const response = await fetch(`${env.apiUrl}/api/v1/profile/blacklist`, {
            headers: buildAuthHeaders({ 'Accept-Language': getActiveApiLocale() }),
          });
          if (response.status === 401) {
            setActiveAccessToken(null);
            resetMockProfileStore();
          } else if (response.ok) {
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
```
*(Make sure `setActiveAccessToken` is imported from `@/api/auth-token` at the top of `profile-api.ts`).*

### Action 3.2 — Reset Profile & Routine Stores on Sign-Out in `mobile/src/features/auth/AuthContext.tsx`
In `mobile/src/features/auth/AuthContext.tsx`:
1. Import `resetMockProfileStore` from `@/features/profile/profile-api` and `resetMockRoutineStore` from `@/features/routine/routine-api`.
2. Inside `persistSession`:
   ```typescript
   if (!next) {
     resetMockProfileStore();
     resetMockRoutineStore();
   }
   ```
3. In `ProfileScreen.tsx`, inside `ProfileScreenContent`:
   Add `isAuthenticated` to the `useEffect` dependency array and reset local state when `!isAuthenticated && !env.useMocks`:
   ```typescript
   useEffect(() => {
     if (!isAuthenticated && !env.useMocks) {
       setSkinType(null);
       setIsPregnant(false);
       setConditions([]);
       setAllergies([]);
       setSavedNotice(false);
       return;
     }
     setSkinType(initialProfile.skin_type);
     setIsPregnant(initialProfile.is_pregnant_or_nursing);
     setConditions(initialProfile.health_conditions);
     setAllergies(initialProfile.allergy_ingredient_ids);
   }, [initialProfile, isAuthenticated]);
   ```

---

## Micro-Step 4: Catch `ProfileAuthRequiredError` in `ProductDetailScreen.tsx`

### Goal
Eliminate `ERROR [Error: Uncaught (in promise) ProfileAuthRequiredError: Authentication required]` when tapping product or ingredient blacklist buttons with an expired or missing token on `ProductDetailScreen`.

### Action 4.1 — Update `handleToggleProductBlacklist` and `handleToggleIngredientBlacklist` in `mobile/src/features/product/product-detail-screen.tsx`
In `mobile/src/features/product/product-detail-screen.tsx`:
1. Import `ProfileAuthRequiredError` from `@/features/profile/profile-api`.
2. Replace `handleToggleProductBlacklist` and `handleToggleIngredientBlacklist` with:

```typescript
  const handleToggleProductBlacklist = async (): Promise<void> => {
    if (!env.useMocks && !getActiveAccessToken()) {
      router.push('/auth/login' as unknown as Href);
      return;
    }
    try {
      await toggleBlacklistProduct.mutateAsync(product.id);
    } catch (err) {
      if (err instanceof ProfileAuthRequiredError) {
        router.push('/auth/login' as unknown as Href);
      }
    }
  };

  const handleToggleIngredientBlacklist = async (ingId: string): Promise<void> => {
    if (!env.useMocks && !getActiveAccessToken()) {
      setSelectedIngredient(null);
      router.push('/auth/login' as unknown as Href);
      return;
    }
    try {
      await toggleBlacklistIngredient.mutateAsync(ingId);
    } catch (err) {
      if (err instanceof ProfileAuthRequiredError) {
        setSelectedIngredient(null);
        router.push('/auth/login' as unknown as Href);
      }
    }
  };
```
3. On the `Pressable` in `ProductDetailScreen.tsx` that calls `handleToggleProductBlacklist`, wrap it as:
```tsx
onPress={() => {
  void handleToggleProductBlacklist();
}}
```
4. On `IngredientRationaleModal`, pass:
```tsx
onToggleBlacklistIngredient={(ingId) => {
  void handleToggleIngredientBlacklist(ingId);
}}
```

---

## Micro-Step 5: Fix Routine API Payload (`422`) & Live Backend Sync (`mobile/src/features/routine/routine-api.ts` & `RoutineScreen.tsx`)

### Goal
1. Fix `PUT /api/v1/routines/${slot}` in `routine-api.ts` so the request body sends `{ steps: normalizedSteps.map((s) => ({ step_order: s.step_order, step_type: s.step_type, product_id: s.product.id })) }`, matching FastAPI's `RoutineStepIn` schema (`extra="forbid"`).
2. Fix `useRoutinesQuery` in `routine-api.ts` so when `!env.useMocks` and `GET /api/v1/routines` returns `200 OK`, missing `morning` or `evening` slots initialize with `steps: []` instead of falling back to fake mock product UUIDs.
3. Deduplicate steps by `product.id` before sending `PUT /api/v1/routines/${slot}` so adding a product that is already in the routine updates its position instead of triggering a `422` duplicate-product error.
4. Update `useRoutineRecommendationsQuery` to fetch real recommendations from `GET /api/v1/routines/recommendations?skin_type=${skinType}` when `!env.useMocks` and authenticated.
5. Add `useRoutineCandidateProductsQuery()` in `routine-api.ts` so `RoutineScreen.tsx` displays real database products from `/api/v1/products/filter?limit=12` when running against the live backend (`!env.useMocks`), while still returning `ROUTINE_CATALOG_CANDIDATES` in mock mode.

### Action 5.1 — Update `mobile/src/features/routine/routine-api.ts`
In `mobile/src/features/routine/routine-api.ts`, replace `useRoutinesQuery`, `useUpdateRoutineMutation`, `useToggleRoutineCompletionMutation`, and `useRoutineRecommendationsQuery`, and export `useRoutineCandidateProductsQuery`:

```typescript
export function useRoutineCandidateProductsQuery(): UseQueryResult<
  readonly CatalogCandidateProduct[],
  Error
> {
  return useQuery({
    queryKey: ['routine-candidates'],
    queryFn: async (): Promise<readonly CatalogCandidateProduct[]> => {
      if (!env.useMocks) {
        try {
          const res = await fetch(`${env.apiUrl}/api/v1/products/filter?limit=12`, {
            headers: buildAuthHeaders({ 'Accept-Language': getActiveApiLocale() }),
          });
          if (res.ok) {
            const page = (await res.json()) as { items?: ProductCard[] };
            if (page.items && page.items.length > 0) {
              return page.items.map((card): CatalogCandidateProduct => {
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
                  product: {
                    ...card,
                    category_slug: card.category_slug ?? null,
                    score_is_estimated: card.score_is_estimated ?? false,
                  },
                  defaultStepType: stepType,
                  activeIngredients:
                    slug === 'serum' ? ['NIACINAMIDE', 'HYALURONIC ACID'] : ['GLYCERIN'],
                };
              });
            }
          }
        } catch {
          // Fall back to static candidates when offline
        }
      }
      return ROUTINE_CATALOG_CANDIDATES;
    },
  });
}

export function useRoutinesQuery(): UseQueryResult<InternalRoutineStore, Error> {
  const token = getActiveAccessToken();
  return useQuery({
    queryKey: ['routines', token ?? 'guest'],
    queryFn: async (): Promise<InternalRoutineStore> => {
      if (!env.useMocks && token) {
        try {
          const res = await fetch(`${env.apiUrl}/api/v1/routines`, {
            headers: buildAuthHeaders({ 'Accept-Language': getActiveApiLocale() }),
          });
          if (res.ok) {
            const data = (await res.json()) as { routines?: RoutineData[] };
            const am = data.routines?.find((r) => r.slot === 'morning') ?? {
              slot: 'morning' as const,
              completed_today: false,
              steps: [],
              conflicts: [],
            };
            const pm = data.routines?.find((r) => r.slot === 'evening') ?? {
              slot: 'evening' as const,
              completed_today: false,
              steps: [],
              conflicts: [],
            };
            routineStore = { morning: am, evening: pm };
            return routineStore;
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
      const seenProductIds = new Set<string>();
      const dedupedSteps = steps.filter((step) => {
        if (seenProductIds.has(step.product.id)) {
          return false;
        }
        seenProductIds.add(step.product.id);
        return true;
      });
      const normalizedSteps = dedupedSteps.map((step, index) => ({
        ...step,
        step_order: index + 1,
      }));
      const conflicts = evaluateRoutineConflicts(normalizedSteps);
      const localUpdated: RoutineData = {
        ...routineStore[slot],
        steps: normalizedSteps,
        conflicts,
      };

      if (!env.useMocks && getActiveAccessToken()) {
        try {
          const apiSteps = normalizedSteps.map((step) => ({
            step_order: step.step_order,
            step_type: step.step_type,
            product_id: step.product.id,
          }));
          const res = await fetch(`${env.apiUrl}/api/v1/routines/${slot}`, {
            method: 'PUT',
            headers: buildAuthHeaders({
              'Content-Type': 'application/json',
              'Accept-Language': getActiveApiLocale(),
            }),
            body: JSON.stringify({ steps: apiSteps }),
          });
          if (res.ok) {
            const serverData = (await res.json()) as RoutineData;
            routineStore = {
              ...routineStore,
              [slot]: serverData,
            };
            return serverData;
          }
        } catch {
          // Fall back to local routine state when offline
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

      if (!env.useMocks && getActiveAccessToken()) {
        try {
          const res = await fetch(`${env.apiUrl}/api/v1/routines/${slot}/complete`, {
            method: 'POST',
            headers: buildAuthHeaders({
              'Accept-Language': getActiveApiLocale(),
            }),
          });
          if (res.ok) {
            const serverData = (await res.json()) as RoutineData;
            routineStore = {
              ...routineStore,
              [slot]: serverData,
            };
            return serverData;
          }
        } catch {
          // Fall back to local routine state when offline
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
```
And update `useRoutineRecommendationsQuery` in `mobile/src/features/routine/routine-api.ts`:
```typescript
export function useRoutineRecommendationsQuery(
  skinType: SkinTypeOption,
): UseQueryResult<RecommendedRoutinesResponse, Error> {
  const token = getActiveAccessToken();
  return useQuery({
    queryKey: ['routine-recommendations', skinType, token ?? 'guest'],
    queryFn: async (): Promise<RecommendedRoutinesResponse> => {
      if (!env.useMocks && token) {
        try {
          const res = await fetch(
            `${env.apiUrl}/api/v1/routines/recommendations?skin_type=${skinType}`,
            {
              headers: buildAuthHeaders({ 'Accept-Language': getActiveApiLocale() }),
            },
          );
          if (res.ok) {
            const serverRec = (await res.json()) as RecommendedRoutinesResponse;
            if (serverRec.morning.length > 0 || serverRec.evening.length > 0) {
              return serverRec;
            }
          }
        } catch {
          // Fall back to local recommendations
        }
      }
      return buildRecommendationsForSkinType(skinType);
    },
  });
}
```
*(Make sure `getActiveAccessToken` is imported alongside `buildAuthHeaders` from `@/api/auth-token` at the top of `routine-api.ts`).*

### Action 5.2 — Use `useRoutineCandidateProductsQuery` in `mobile/src/features/routine/RoutineScreen.tsx`
In `mobile/src/features/routine/RoutineScreen.tsx`:
1. Import `useRoutineCandidateProductsQuery` alongside `ROUTINE_CATALOG_CANDIDATES` from `./routine-api`.
2. Call `const candidatesQuery = useRoutineCandidateProductsQuery();` inside `RoutineScreen` and define `const candidates = candidatesQuery.data ?? ROUTINE_CATALOG_CANDIDATES;`.
3. Replace `ROUTINE_CATALOG_CANDIDATES.map((candidate) => ...)` with `candidates.map((candidate) => ...)`.

---

## Micro-Step 6: Upgrade Multi-Ingredient Include & Exclude Filter UI (`ProductCatalogScreen.tsx` & `search-api.ts`)

### Goal
Allow users to add as many included and excluded ingredients as they want on `ProductCatalogScreen.tsx` via dedicated **"+ Add included ingredient"** and **"+ Add excluded ingredient"** buttons under each input, display active ingredient chips with one-tap removal (`×`), and pass all included/excluded ingredients to `useCatalogProductsQuery`.

### Action 6.1 — Update `CatalogFilterParams` and `useCatalogProductsQuery` in `mobile/src/features/search/search-api.ts`
Replace `mobile/src/features/search/search-api.ts` with:

```typescript
import { useQuery, type UseQueryResult } from '@tanstack/react-query';
import { buildAuthHeaders } from '@/api/auth-token';
import { productCardsFixture } from '@/api/fixtures';
import { getActiveApiLocale } from '@/api/locale';
import type { ProductCard, RiskLevel } from '@/api/types';
import { env } from '@/config/env';

export interface CatalogFilterParams {
  readonly query?: string;
  readonly category?: string | null;
  readonly band?: RiskLevel | null;
  readonly minScore?: number | null;
  readonly includeIngredient?: string;
  readonly excludeIngredient?: string;
  readonly includeIngredients?: readonly string[];
  readonly excludeIngredients?: readonly string[];
}

function normalizeIngredientTerms(
  single?: string,
  list?: readonly string[],
): string[] {
  const combined: string[] = [];
  for (const item of list ?? []) {
    for (const part of item.split(',')) {
      const trimmed = part.trim();
      if (trimmed && !combined.some((existing) => existing.toLowerCase() === trimmed.toLowerCase())) {
        combined.push(trimmed);
      }
    }
  }
  if (single) {
    for (const part of single.split(',')) {
      const trimmed = part.trim();
      if (trimmed && !combined.some((existing) => existing.toLowerCase() === trimmed.toLowerCase())) {
        combined.push(trimmed);
      }
    }
  }
  return combined;
}

export function filterLocalCatalogProducts(params: CatalogFilterParams): ProductCard[] {
  const qNorm = (params.query ?? '').trim().toLowerCase();
  const incTerms = normalizeIngredientTerms(
    params.includeIngredient,
    params.includeIngredients,
  ).map((t) => t.toLowerCase());
  const excTerms = normalizeIngredientTerms(
    params.excludeIngredient,
    params.excludeIngredients,
  ).map((t) => t.toLowerCase());

  return productCardsFixture.filter((product) => {
    if (qNorm) {
      const hay =
        `${product.name} ${product.brand ?? ''} ${product.category_slug ?? ''}`.toLowerCase();
      if (!hay.includes(qNorm)) {
        return false;
      }
    }
    if (params.category && product.category_slug !== params.category) {
      return false;
    }
    if (params.band && product.score_band !== params.band) {
      return false;
    }
    if (
      params.minScore !== null &&
      params.minScore !== undefined &&
      (product.score === null || product.score < params.minScore)
    ) {
      return false;
    }
    if (incTerms.includes('parfum') && product.score_band === 'low') {
      return false;
    }
    if (excTerms.includes('parfum') && product.score_band === 'unknown') {
      return false;
    }
    return true;
  });
}

export function useCatalogProductsQuery(
  params: CatalogFilterParams,
): UseQueryResult<ProductCard[], Error> {
  const includeTerms = normalizeIngredientTerms(
    params.includeIngredient,
    params.includeIngredients,
  );
  const excludeTerms = normalizeIngredientTerms(
    params.excludeIngredient,
    params.excludeIngredients,
  );

  const normalizedKey = {
    query: (params.query ?? '').trim(),
    category: params.category ?? null,
    band: params.band ?? null,
    minScore: params.minScore ?? null,
    include: includeTerms,
    exclude: excludeTerms,
  };

  return useQuery({
    queryKey: ['catalog-products', normalizedKey],
    queryFn: async (): Promise<ProductCard[]> => {
      if (!env.useMocks) {
        try {
          const validIncludes = includeTerms.filter((s) => s.length >= 2);
          const validExcludes = excludeTerms.filter((s) => s.length >= 2);

          const hasFacetFilters = Boolean(
            normalizedKey.category ||
              normalizedKey.band ||
              normalizedKey.minScore !== null ||
              validIncludes.length > 0 ||
              validExcludes.length > 0,
          );

          if (normalizedKey.query && !hasFacetFilters) {
            const url = new URL(`${env.apiUrl}/api/v1/products/search`);
            url.searchParams.set('q', normalizedKey.query);
            url.searchParams.set('limit', '50');
            const res = await fetch(url.toString(), {
              headers: buildAuthHeaders({ 'Accept-Language': getActiveApiLocale() }),
            });
            if (res.ok) {
              const page = (await res.json()) as { items?: ProductCard[] };
              return (page.items ?? []).map((item) => ({
                ...item,
                category_slug: item.category_slug ?? null,
                score_is_estimated: item.score_is_estimated ?? false,
              }));
            }
          } else {
            const url = new URL(`${env.apiUrl}/api/v1/products/filter`);
            url.searchParams.set('limit', '50');
            if (normalizedKey.query) {
              url.searchParams.set('q', normalizedKey.query);
            }
            if (normalizedKey.category) {
              url.searchParams.set('category', normalizedKey.category);
            }
            if (normalizedKey.band) {
              url.searchParams.set('band', normalizedKey.band);
            }
            if (normalizedKey.minScore !== null) {
              url.searchParams.set('min_score', String(normalizedKey.minScore));
            }
            for (const term of validIncludes) {
              url.searchParams.append('include', term);
            }
            for (const term of validExcludes) {
              url.searchParams.append('exclude', term);
            }

            const res = await fetch(url.toString(), {
              headers: buildAuthHeaders({ 'Accept-Language': getActiveApiLocale() }),
            });
            if (res.ok) {
              const page = (await res.json()) as { items?: ProductCard[] };
              return (page.items ?? []).map((item) => ({
                ...item,
                category_slug: item.category_slug ?? normalizedKey.category ?? null,
                score_is_estimated: item.score_is_estimated ?? false,
              }));
            }
          }
        } catch {
          // Fall back to deterministic local filter
        }
      }
      return filterLocalCatalogProducts(params);
    },
  });
}
```

### Action 6.2 — Update `mobile/src/features/search/ProductCatalogScreen.tsx`
Replace `mobile/src/features/search/ProductCatalogScreen.tsx` with the following implementation containing the "+ Add included ingredient" and "+ Add excluded ingredient" buttons and removable ingredient chips under each input:

```typescript
import { useRouter, type Href } from 'expo-router';
import { useState, type ReactElement } from 'react';
import { Pressable, StyleSheet, Text, TextInput, View } from 'react-native';
import type { RiskLevel } from '@/api/types';
import { EmptyState, ErrorState, ProductCard, Screen, Skeleton } from '@/components';
import { getProductArtwork } from '@/features/home/product-artwork';
import { getLocalizedCategorySlug } from '@/i18n/category';
import { useTranslation } from '@/i18n/useTranslation';
import { radii, spacing, typography, useThemeColors } from '@/theme/tokens';
import { useCatalogProductsQuery } from './search-api';

const FILTER_CATEGORIES = [
  'cleanser',
  'toner',
  'serum',
  'moisturizer',
  'sunscreen',
  'eye-care',
  'body-lotion',
  'lip-care',
] as const;

const FILTER_BANDS: readonly RiskLevel[] = ['low', 'moderate', 'high'];
const MIN_SCORES: readonly (number | null)[] = [null, 50, 75];

export interface ProductCatalogScreenProps {
  readonly initialCategory?: string;
}

export function ProductCatalogScreen({ initialCategory }: ProductCatalogScreenProps): ReactElement {
  const router = useRouter();
  const colors = useThemeColors();
  const { t } = useTranslation();

  const [query, setQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string | null>(initialCategory ?? null);
  const [selectedBand, setSelectedBand] = useState<RiskLevel | null>(null);
  const [minScore, setMinScore] = useState<number | null>(null);
  const [includeIngredient, setIncludeIngredient] = useState('');
  const [excludeIngredient, setExcludeIngredient] = useState('');
  const [includedIngredients, setIncludedIngredients] = useState<string[]>([]);
  const [excludedIngredients, setExcludedIngredients] = useState<string[]>([]);

  const catalogQuery = useCatalogProductsQuery({
    query,
    category: selectedCategory,
    band: selectedBand,
    minScore,
    includeIngredient,
    excludeIngredient,
    includeIngredients: includedIngredients,
    excludeIngredients: excludedIngredients,
  });

  const handleAddIncludedIngredient = (): void => {
    const trimmed = includeIngredient.trim();
    if (!trimmed) {
      return;
    }
    setIncludedIngredients((prev) =>
      prev.some((item) => item.toLowerCase() === trimmed.toLowerCase())
        ? prev
        : [...prev, trimmed],
    );
    setIncludeIngredient('');
  };

  const handleRemoveIncludedIngredient = (name: string): void => {
    setIncludedIngredients((prev) => prev.filter((item) => item !== name));
  };

  const handleAddExcludedIngredient = (): void => {
    const trimmed = excludeIngredient.trim();
    if (!trimmed) {
      return;
    }
    setExcludedIngredients((prev) =>
      prev.some((item) => item.toLowerCase() === trimmed.toLowerCase())
        ? prev
        : [...prev, trimmed],
    );
    setExcludeIngredient('');
  };

  const handleRemoveExcludedIngredient = (name: string): void => {
    setExcludedIngredients((prev) => prev.filter((item) => item !== name));
  };

  const handleResetFilters = (): void => {
    setQuery('');
    setSelectedCategory(null);
    setSelectedBand(null);
    setMinScore(null);
    setIncludeIngredient('');
    setExcludeIngredient('');
    setIncludedIngredients([]);
    setExcludedIngredients([]);
  };

  const products = catalogQuery.data ?? [];

  return (
    <Screen contentContainerStyle={styles.content}>
      <Pressable
        accessibilityRole="button"
        accessibilityLabel={t('auth.back_home')}
        onPress={() => router.push('/' as unknown as Href)}
        style={[styles.backButton, { borderColor: colors.border }]}
      >
        <Text style={[styles.backText, { color: colors.primary }]}>‹ {t('auth.back_home')}</Text>
      </Pressable>

      <Text accessibilityRole="header" style={[styles.title, { color: colors.text }]}>
        {t('search.title')}
      </Text>

      <View style={styles.searchGroup}>
        <Text style={[styles.label, { color: colors.text }]}>{t('search.query_label')}</Text>
        <TextInput
          accessibilityLabel={t('search.query_label')}
          autoCapitalize="none"
          autoCorrect={false}
          onChangeText={setQuery}
          placeholder={t('search.query_placeholder')}
          placeholderTextColor={colors.textMuted}
          returnKeyType="search"
          style={[
            styles.input,
            {
              color: colors.text,
              backgroundColor: colors.surface,
              borderColor: colors.border,
            },
          ]}
          value={query}
        />
      </View>

      <Text style={[styles.label, { color: colors.text }]}>{t('search.category_heading')}</Text>
      <View style={styles.pillsRow}>
        <Pressable
          accessibilityRole="button"
          accessibilityLabel={t('search.all_categories')}
          accessibilityState={{ selected: selectedCategory === null }}
          onPress={() => setSelectedCategory(null)}
          style={[
            styles.pill,
            {
              backgroundColor: selectedCategory === null ? colors.primary : colors.surface,
              borderColor: selectedCategory === null ? colors.primary : colors.border,
            },
          ]}
        >
          <Text
            style={[
              styles.pillText,
              { color: selectedCategory === null ? colors.onPrimary : colors.text },
            ]}
          >
            {t('search.all_categories')}
          </Text>
        </Pressable>
        {FILTER_CATEGORIES.map((slug) => {
          const selected = selectedCategory === slug;
          const label = getLocalizedCategorySlug(slug) ?? slug;
          return (
            <Pressable
              key={slug}
              accessibilityRole="button"
              accessibilityLabel={label}
              accessibilityState={{ selected }}
              onPress={() => setSelectedCategory(selected ? null : slug)}
              style={[
                styles.pill,
                {
                  backgroundColor: selected ? colors.primary : colors.surface,
                  borderColor: selected ? colors.primary : colors.border,
                },
              ]}
            >
              <Text style={[styles.pillText, { color: selected ? colors.onPrimary : colors.text }]}>
                {label}
              </Text>
            </Pressable>
          );
        })}
      </View>

      <Text style={[styles.label, { color: colors.text }]}>{t('search.band_heading')}</Text>
      <View style={styles.pillsRow}>
        {FILTER_BANDS.map((band) => {
          const selected = selectedBand === band;
          const label = t(`risk.${band}`);
          return (
            <Pressable
              key={band}
              accessibilityRole="button"
              accessibilityLabel={label}
              accessibilityState={{ selected }}
              onPress={() => setSelectedBand(selected ? null : band)}
              style={[
                styles.pill,
                {
                  backgroundColor: selected ? colors.primary : colors.surface,
                  borderColor: selected ? colors.primary : colors.border,
                },
              ]}
            >
              <Text style={[styles.pillText, { color: selected ? colors.onPrimary : colors.text }]}>
                {label}
              </Text>
            </Pressable>
          );
        })}
      </View>

      <Text style={[styles.label, { color: colors.text }]}>{t('search.min_score_heading')}</Text>
      <View style={styles.pillsRow}>
        {MIN_SCORES.map((scoreVal) => {
          const selected = minScore === scoreVal;
          const label =
            scoreVal === null
              ? t('search.score_any')
              : scoreVal === 50
                ? t('search.score_50')
                : t('search.score_75');
          return (
            <Pressable
              key={String(scoreVal)}
              accessibilityRole="button"
              accessibilityLabel={label}
              accessibilityState={{ selected }}
              onPress={() => setMinScore(scoreVal)}
              style={[
                styles.pill,
                {
                  backgroundColor: selected ? colors.primary : colors.surface,
                  borderColor: selected ? colors.primary : colors.border,
                },
              ]}
            >
              <Text style={[styles.pillText, { color: selected ? colors.onPrimary : colors.text }]}>
                {label}
              </Text>
            </Pressable>
          );
        })}
      </View>

      <View style={styles.ingredientFiltersRow}>
        <View style={styles.ingredientFilterCol}>
          <Text style={[styles.smallLabel, { color: colors.text }]}>
            {t('search.include_label')}
          </Text>
          <TextInput
            accessibilityLabel={t('search.include_label')}
            autoCapitalize="none"
            autoCorrect={false}
            onChangeText={setIncludeIngredient}
            onSubmitEditing={handleAddIncludedIngredient}
            placeholder={t('search.include_placeholder')}
            placeholderTextColor={colors.textMuted}
            returnKeyType="done"
            style={[
              styles.smallInput,
              {
                color: colors.text,
                backgroundColor: colors.surface,
                borderColor: colors.border,
              },
            ]}
            value={includeIngredient}
          />
          <Pressable
            accessibilityRole="button"
            accessibilityLabel={t('search.add_include_button')}
            onPress={handleAddIncludedIngredient}
            style={({ pressed }) => [
              styles.addIngredientButton,
              {
                borderColor: colors.primary,
                backgroundColor: colors.surface,
                opacity: pressed ? 0.75 : 1,
              },
            ]}
          >
            <Text style={[styles.addIngredientButtonText, { color: colors.primary }]}>
              {t('search.add_include_button')}
            </Text>
          </Pressable>
          {includedIngredients.length > 0 ? (
            <View style={styles.chipsWrap}>
              {includedIngredients.map((item) => (
                <Pressable
                  key={`inc-${item}`}
                  accessibilityRole="button"
                  accessibilityLabel={t('search.remove_include_chip', { name: item })}
                  onPress={() => handleRemoveIncludedIngredient(item)}
                  style={[
                    styles.ingredientChip,
                    { backgroundColor: colors.lowSurface, borderColor: colors.low },
                  ]}
                >
                  <Text style={[styles.ingredientChipText, { color: colors.low }]}>
                    ✓ {item} ×
                  </Text>
                </Pressable>
              ))}
            </View>
          ) : null}
        </View>

        <View style={styles.ingredientFilterCol}>
          <Text style={[styles.smallLabel, { color: colors.text }]}>
            {t('search.exclude_label')}
          </Text>
          <TextInput
            accessibilityLabel={t('search.exclude_label')}
            autoCapitalize="none"
            autoCorrect={false}
            onChangeText={setExcludeIngredient}
            onSubmitEditing={handleAddExcludedIngredient}
            placeholder={t('search.exclude_placeholder')}
            placeholderTextColor={colors.textMuted}
            returnKeyType="done"
            style={[
              styles.smallInput,
              {
                color: colors.text,
                backgroundColor: colors.surface,
                borderColor: colors.border,
              },
            ]}
            value={excludeIngredient}
          />
          <Pressable
            accessibilityRole="button"
            accessibilityLabel={t('search.add_exclude_button')}
            onPress={handleAddExcludedIngredient}
            style={({ pressed }) => [
              styles.addIngredientButton,
              {
                borderColor: colors.high,
                backgroundColor: colors.surface,
                opacity: pressed ? 0.75 : 1,
              },
            ]}
          >
            <Text style={[styles.addIngredientButtonText, { color: colors.high }]}>
              {t('search.add_exclude_button')}
            </Text>
          </Pressable>
          {excludedIngredients.length > 0 ? (
            <View style={styles.chipsWrap}>
              {excludedIngredients.map((item) => (
                <Pressable
                  key={`exc-${item}`}
                  accessibilityRole="button"
                  accessibilityLabel={t('search.remove_exclude_chip', { name: item })}
                  onPress={() => handleRemoveExcludedIngredient(item)}
                  style={[
                    styles.ingredientChip,
                    { backgroundColor: colors.highSurface, borderColor: colors.high },
                  ]}
                >
                  <Text style={[styles.ingredientChipText, { color: colors.high }]}>
                    ⬟ {item} ×
                  </Text>
                </Pressable>
              ))}
            </View>
          ) : null}
        </View>
      </View>

      <View style={styles.metaRow}>
        <Text style={[styles.countText, { color: colors.textMuted }]}>
          {t('search.results_count', { count: products.length })}
        </Text>
        <Pressable
          accessibilityRole="button"
          accessibilityLabel={t('search.clear_filters')}
          onPress={handleResetFilters}
          style={[styles.resetButton, { borderColor: colors.border }]}
        >
          <Text style={[styles.resetText, { color: colors.primary }]}>
            {t('search.clear_filters')}
          </Text>
        </Pressable>
      </View>

      {catalogQuery.isPending ? (
        <View style={styles.list}>
          <Skeleton height={116} />
          <Skeleton height={116} />
        </View>
      ) : catalogQuery.isError ? (
        <ErrorState
          onRetry={() => {
            void catalogQuery.refetch();
          }}
        />
      ) : products.length === 0 ? (
        <EmptyState title={t('search.empty_title')} description={t('search.empty_description')} />
      ) : (
        <View style={styles.list}>
          {products.map((product) => (
            <ProductCard
              key={product.id}
              product={product}
              artwork={getProductArtwork(product.category_slug)}
              onPress={(id) =>
                router.push({
                  pathname: '/products/[productId]',
                  params: { productId: id },
                } as unknown as Href)
              }
            />
          ))}
        </View>
      )}
    </Screen>
  );
}

const styles = StyleSheet.create({
  content: { padding: spacing.lg, gap: spacing.md, paddingBottom: spacing.xxxl },
  backButton: {
    minHeight: 44,
    alignSelf: 'flex-start',
    justifyContent: 'center',
    paddingHorizontal: spacing.md,
    borderWidth: 1,
    borderRadius: radii.md,
  },
  backText: {
    fontSize: typography.size.sm,
    fontWeight: typography.weight.semibold,
  },
  title: {
    fontSize: typography.size.xl,
    lineHeight: typography.lineHeight.xl,
    fontWeight: typography.weight.bold,
  },
  searchGroup: {
    gap: spacing.xs,
  },
  label: {
    fontSize: typography.size.sm,
    fontWeight: typography.weight.bold,
  },
  smallLabel: {
    fontSize: typography.size.xs,
    fontWeight: typography.weight.semibold,
  },
  input: {
    minHeight: 48,
    borderWidth: 1,
    borderRadius: radii.md,
    paddingHorizontal: spacing.md,
    fontSize: typography.size.md,
  },
  smallInput: {
    minHeight: 44,
    borderWidth: 1,
    borderRadius: radii.md,
    paddingHorizontal: spacing.sm,
    fontSize: typography.size.sm,
  },
  addIngredientButton: {
    minHeight: 44,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderRadius: radii.md,
    paddingHorizontal: spacing.sm,
  },
  addIngredientButtonText: {
    fontSize: typography.size.xs,
    fontWeight: typography.weight.semibold,
  },
  chipsWrap: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.xs,
  },
  ingredientChip: {
    minHeight: 44,
    justifyContent: 'center',
    paddingHorizontal: spacing.sm,
    borderWidth: 1,
    borderRadius: radii.pill,
  },
  ingredientChipText: {
    fontSize: typography.size.xs,
    fontWeight: typography.weight.semibold,
  },
  pillsRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.sm,
  },
  pill: {
    minHeight: 44,
    justifyContent: 'center',
    paddingHorizontal: spacing.md,
    borderWidth: 1,
    borderRadius: radii.pill,
  },
  pillText: {
    fontSize: typography.size.xs,
    fontWeight: typography.weight.semibold,
  },
  ingredientFiltersRow: {
    flexDirection: 'row',
    gap: spacing.sm,
  },
  ingredientFilterCol: {
    flex: 1,
    gap: spacing.xs,
  },
  metaRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: spacing.sm,
  },
  countText: {
    fontSize: typography.size.xs,
    fontWeight: typography.weight.medium,
  },
  resetButton: {
    minHeight: 44,
    justifyContent: 'center',
    paddingHorizontal: spacing.md,
    borderWidth: 1,
    borderRadius: radii.md,
  },
  resetText: {
    fontSize: typography.size.xs,
    fontWeight: typography.weight.semibold,
  },
  list: {
    gap: spacing.md,
  },
});
```

---

## Micro-Step 7: Add Unit & Integration Tests for Multi-Ingredient Chips & Sign-Out Profile Reset

### Action 7.1 — Update `mobile/src/features/search/ProductCatalogScreen.test.tsx`
Replace `mobile/src/features/search/ProductCatalogScreen.test.tsx` with:

```typescript
import type { ReactElement } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, waitFor } from '@testing-library/react-native';
import i18n from '@/i18n/i18n';
import { LanguageProvider } from '@/i18n/LanguageProvider';
import { ProductCatalogScreen } from './ProductCatalogScreen';

const mockPush = jest.fn();

jest.mock('@/config/env', () => ({
  env: { apiUrl: 'https://mock.invalid', useMocks: true },
}));

jest.mock('expo-router', () => ({
  useRouter: () => ({ push: mockPush }),
}));

function renderCatalog(initialCategory?: string): ReactElement {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: false, gcTime: 0 },
    },
  });
  return (
    <QueryClientProvider client={client}>
      <LanguageProvider>
        <ProductCatalogScreen initialCategory={initialCategory} />
      </LanguageProvider>
    </QueryClientProvider>
  );
}

describe('ProductCatalogScreen (US-05, US-06)', () => {
  beforeEach(() => {
    mockPush.mockClear();
  });

  it('filters products by search query and resets filters', async () => {
    const screen = await render(renderCatalog());
    await screen.findByText(i18n.t('search.title'));
    await screen.findByText('Daily Hydration Serum');

    const input = screen.getByLabelText(i18n.t('search.query_label'));
    await fireEvent.changeText(input, 'Sunscreen');

    await waitFor(() => {
      expect(screen.getByText('Daily Mineral Sunscreen SPF 50')).toBeTruthy();
      expect(screen.queryByText('Daily Hydration Serum')).toBeNull();
    });

    await fireEvent.press(screen.getByRole('button', { name: i18n.t('search.clear_filters') }));

    await waitFor(() => {
      expect(screen.getByText('Daily Hydration Serum')).toBeTruthy();
    });
  });

  it('adds multiple included and excluded ingredient chips via the add buttons and removes them', async () => {
    const screen = await render(renderCatalog());
    await screen.findByText(i18n.t('search.title'));

    const includeInput = screen.getByLabelText(i18n.t('search.include_label'));
    const addIncludeBtn = screen.getByRole('button', {
      name: i18n.t('search.add_include_button'),
    });

    await fireEvent.changeText(includeInput, 'Niacinamide');
    await fireEvent.press(addIncludeBtn);

    await fireEvent.changeText(includeInput, 'Glycerin');
    await fireEvent.press(addIncludeBtn);

    expect(
      screen.getByRole('button', {
        name: i18n.t('search.remove_include_chip', { name: 'Niacinamide' }),
      }),
    ).toBeTruthy();
    expect(
      screen.getByRole('button', {
        name: i18n.t('search.remove_include_chip', { name: 'Glycerin' }),
      }),
    ).toBeTruthy();

    const excludeInput = screen.getByLabelText(i18n.t('search.exclude_label'));
    const addExcludeBtn = screen.getByRole('button', {
      name: i18n.t('search.add_exclude_button'),
    });

    await fireEvent.changeText(excludeInput, 'Parfum');
    await fireEvent.press(addExcludeBtn);

    const parfumChip = screen.getByRole('button', {
      name: i18n.t('search.remove_exclude_chip', { name: 'Parfum' }),
    });
    expect(parfumChip).toBeTruthy();

    await fireEvent.press(parfumChip);
    expect(
      screen.queryByRole('button', {
        name: i18n.t('search.remove_exclude_chip', { name: 'Parfum' }),
      }),
    ).toBeNull();
  });

  it('pre-filters by initialCategory when navigated from HomeScreen', async () => {
    const screen = await render(renderCatalog('cleanser'));
    await screen.findByText('Gentle Cream Cleanser');

    expect(screen.queryByText('Cloud Cream Moisturizer')).toBeNull();
  });
});
```

### Action 7.2 — Add Sign-Out Profile Reset Test to `mobile/src/features/profile/ProfileScreen.test.tsx`
In `mobile/src/features/profile/ProfileScreen.test.tsx`, add a test verifying that signing out resets the profile store (`resetMockProfileStore`):

```typescript
  it('resets profile selections when signing out', async () => {
    const screen = await render(renderProfile());
    await screen.findByText(i18n.t('profile.title'));

    const sensitivePill = screen.getByRole('button', {
      name: i18n.t('profile.skin_types.sensitive'),
    });
    await fireEvent.press(sensitivePill);
    await fireEvent.press(screen.getByRole('button', { name: i18n.t('profile.save_button') }));

    await waitFor(() => {
      expect(screen.getByText(i18n.t('profile.saved_confirmation'))).toBeTruthy();
    });

    resetMockProfileStore();
    const freshScreen = await render(renderProfile());
    await freshScreen.findByText(i18n.t('profile.title'));
    expect(
      freshScreen.getByRole('button', { name: i18n.t('profile.skin_types.sensitive') }).props
        .accessibilityState?.selected,
    ).toBe(false);
  });
```

---

## Micro-Step 8: Run All Backend, Mobile & Pre-Commit Quality Gates

Execute the following commands in order and fix any formatting, lint, or type issue until every single command exits with code `0`:

```bash
# 1. Backend quality gates & tests
cd backend
uv run ruff check --fix .
uv run ruff format .
uv run mypy
uv run lint-imports
uv run pytest

# 2. Mobile quality gates & tests
cd ../mobile
npm run format
npm run check
npx expo install --check

# 3. Repository-wide pre-commit hooks
cd ../backend
uv run pre-commit run --all-files
```

---

## Final Completion Checklist (Must All Be True Before Finishing)

- [ ] `ProductDetailScreen.tsx` catches `ProfileAuthRequiredError` on both product and ingredient blacklist toggles and redirects to `/auth/login` with zero uncaught promise errors.
- [ ] `PUT /api/v1/routines/{slot}` sends `{ step_order, step_type, product_id }` and never triggers HTTP `422`.
- [ ] `POST /api/v1/routines/{slot}/complete` uses `get_or_create_for_user_slot` on the backend and never triggers HTTP `404`.
- [ ] Signing out (`signOut()`) calls `resetMockProfileStore()` and `resetMockRoutineStore()`, and remounts `ProfileScreen` with all skin types, pregnancy toggle, conditions, allergies, and blacklisted items reset.
- [ ] `ProductCatalogScreen.tsx` renders "+ Add included ingredient" and "+ Add excluded ingredient" buttons under their respective inputs, displays removable chips for each added ingredient, and sends all included/excluded ingredients to `/api/v1/products/filter`.
- [ ] `uv run pytest` (Backend), `npm run check` (Mobile), and `uv run pre-commit run --all-files` all exit with code `0`.
