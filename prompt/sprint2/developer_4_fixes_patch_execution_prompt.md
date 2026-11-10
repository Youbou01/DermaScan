# System Role & Execution Mandate (For Coding Agent: Gemini 3.8 Flash)

You are **Developer 4 (Mobile Track B)** on the **DermaScan** project (Expo SDK 58, React Native 0.88, Expo Router, TypeScript strict, TanStack Query v5, i18next, Jest + React Native Testing Library).

Your objective is to harden and patch the current implementation of **Mobile Track B** (`MOB-S2-5` through `MOB-S2-8`). The previous execution established the screens, but an audit revealed **4 architectural & UX flaws** that must be resolved:

1. **Button Disable & Concurrency Guard in `RoutineScreen.tsx`:** Rapidly tapping `+ Add candidate` or `Remove` causes state-clobbering race conditions because the action buttons remain enabled while `updateRoutine.isPending` is true.
2. **Missing Real HTTP Sync in `routine-api.ts`:** `useUpdateRoutineMutation` and `useToggleRoutineCompletionMutation` only modify local in-memory variables and invalidate queries. When `env.useMocks === false` and the backend is live, `queryClient.invalidateQueries` immediately re-fetches stale server data, reverting user edits.
3. **Dead Translation Key Wiring (`conflicts.pre_check_warning`):** Candidate cards on `RoutineScreen.tsx` do not display pre-addition conflict warnings before a conflicting product is clicked.
4. **Jest Worker Timer Leak / Open Handles:** In `OcrScanScreen.test.tsx` and `RoutineScreen.test.tsx`, `new QueryClient()` does not disable garbage-collection timers (`gcTime: 0`), resulting in the Jest warning *"A worker process has failed to exit gracefully"*.

---

## Strict Operating Rules

1. **Isolation:**
   - **NEVER touch `backend/`.**
   - **NEVER edit `mobile/src/api/client.ts` or `mobile/src/api/hooks.ts`** (Developer 3 owns them).
   - Confine all work strictly to `mobile/src/features/routine/`, `mobile/src/features/scan/`, and their matching tests.
2. **Code Standards:**
   - No `any`, explicit return types on every function and component, inline type imports, no floating promises.
   - Forbidden words gate: Never introduce `safe`, `unsafe`, `toxic`, `harmful`, or `dangerous` in any string or code comment.
3. **Quality Gate:**
   - Must run `npm run format`, `npm run typecheck`, `npm run lint`, and `npm test` inside `mobile/`. All must exit with code 0.

---

## Phase 0: Pre-Flight Check

Run from repository root:
```bash
cd mobile
npm run check
```
Verify that all 12 test suites currently pass before applying the fixes.

---

## Micro-Step 1: Fix Real HTTP Backend Sync in `mobile/src/features/routine/routine-api.ts`

### Root Cause
`useUpdateRoutineMutation` and `useToggleRoutineCompletionMutation` modify in-memory `routineStore` without sending `PUT /api/v1/routines/{slot}` or `POST /api/v1/routines/{slot}/complete` when `env.useMocks === false`.

### Implementation Requirements
In `mobile/src/features/routine/routine-api.ts`:
1. Update `useUpdateRoutineMutation` mutation function:
   - When `!env.useMocks`:
     - Send a `PUT` request to `${env.apiUrl}/api/v1/routines/${slot}` with `{ steps: normalizedSteps }` and headers `{ "Content-Type": "application/json", "Accept-Language": getActiveApiLocale() }`.
     - Wrap in a `try...catch` block: if the response is `ok`, parse and return the response `RoutineData`; if network fails or status is `404` (backend not ready yet), log a warning and fall back to the in-memory store.
   - When `env.useMocks`:
     - Update `routineStore[slot]` directly as currently implemented.
2. Update `useToggleRoutineCompletionMutation` mutation function:
   - When `!env.useMocks`:
     - Send a `POST` request to `${env.apiUrl}/api/v1/routines/${slot}/complete` with headers `{ "Accept-Language": getActiveApiLocale() }`.
     - In `catch`, fall back gracefully to local `routineStore`.
3. Add a helper function `checkCandidateConflict(candidate: CatalogCandidateProduct, currentSteps: readonly RoutineStepItem[]): RoutineConflict | null`:
   - Simulates adding `candidate` to `currentSteps` by creating a hypothetical step and passing the combined list to `evaluateRoutineConflicts`.
   - Returns the first detected conflict involving `candidate.product.id`, or `null` if none.

---

## Micro-Step 2: Add Concurrency Guards & Pre-Addition Conflict Warnings in `RoutineScreen.tsx`

### Root Cause
1. Fast user taps allow multiple mutations to fire in parallel, overwriting array state.
2. `conflicts.pre_check_warning` in `en.json`/`fr.json` is unused.

### Implementation Requirements
In `mobile/src/features/routine/RoutineScreen.tsx`:
1. Inspect mutation states:
   ```typescript
   const isMutating = updateRoutine.isPending || toggleCompletion.isPending;
   ```
2. Disable buttons during mutation:
   - Candidate `Pressable` rows: add `disabled={isMutating}`, apply `opacity: pressed || isMutating ? 0.6 : 1`.
   - Step `↑`, `↓`, and `×` action buttons: add `disabled={isMutating || ...}` and reduce opacity when disabled.
   - Habit toggle button: add `disabled={isMutating}`.
3. Pre-addition conflict indicator:
   - On each candidate row in the catalog candidates list, call:
     ```typescript
     const preConflict = checkCandidateConflict(candidate, steps);
     ```
   - If `preConflict` is not null:
     - Render an inline caution tag above or next to the candidate title:
       ```tsx
       <Text style={[styles.preConflictTag, { color: colors.moderate }]}>
         ⚠ {t('conflicts.pre_check_warning')} ({preConflict.title})
       </Text>
       ```
     - Style `preConflictTag` with `fontSize: typography.size.xs`, `fontWeight: '600'`, `marginBottom: 2`.

---

## Micro-Step 3: Eliminate Jest Timer Leaks in Test Files

### Root Cause
In `OcrScanScreen.test.tsx` and `RoutineScreen.test.tsx`, `new QueryClient()` uses default `gcTime` (5 minutes) with active timer handles, triggering the Jest warning `A worker process has failed to exit gracefully`.

### Implementation Requirements
1. In `mobile/src/features/scan/OcrScanScreen.test.tsx`:
   Update `new QueryClient(...)`:
   ```typescript
   const queryClient = new QueryClient({
     defaultOptions: {
       queries: { retry: false, gcTime: 0 },
       mutations: { retry: false, gcTime: 0 },
     },
   });
   ```
2. In `mobile/src/features/routine/RoutineScreen.test.tsx`:
   Update `createTestQueryClient()`:
   ```typescript
   function createTestQueryClient(): QueryClient {
     return new QueryClient({
       defaultOptions: {
         queries: { retry: false, gcTime: 0 },
         mutations: { retry: false, gcTime: 0 },
       },
     });
   }
   ```
3. In `mobile/src/features/routine/RoutineScreen.test.tsx`:
   Add a test case verifying the pre-addition conflict indicator:
   - Test name: `it('displays pre-check conflict warning on conflicting candidate product before addition', async () => ...)`
   - Verify that when the routine already contains `Glycolic Acid 7% Resurfacing Toner`, the candidate card for `Night Renewal Retinol 0.3% Serum` displays the text from `i18n.t('conflicts.pre_check_warning')`.

---

## Micro-Step 4: Quality Gate Execution & Verification

Run the complete verification commands in `mobile/`:
```bash
cd mobile
npm run format
npm run typecheck
npm run lint
npm test
npm run check
```

Confirm that:
- [ ] `tsc --noEmit` exits with 0 errors.
- [ ] `eslint . --max-warnings=0` exits with 0 warnings.
- [ ] `prettier --check .` reports all files match Prettier style.
- [ ] Jest passes with 0 failures and without the worker leak warning.
- [ ] Zero files outside `mobile/` or inside `mobile/src/api/` were modified.
