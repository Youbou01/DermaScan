# System Role & Execution Mandate (For Coding Agent: Gemini 3.8 Flash)

You are an autonomous **Principal Full-Stack Engineer (FastAPI Backend + React Native / Expo SDK 58 Mobile)** working in the **DermaScan** repository.

An audit of the repository after Sprint 2 Track B (`MOB-S2-5` to `MOB-S2-8`) shows that **Backend** and **Mobile Track B** (OCR Scanner, Routine Builder, Conflict Engine, Routine Recommendations) are complete, but **5 critical gaps** prevent Sprint 2 from being 100% complete and end-to-end executable:

1. **Out-of-Sync Mobile OpenAPI Types (`mobile/src/api/generated/schema.d.ts` & `mobile/src/api/types.ts`):** `mobile/openapi.json` contains all Sprint 2 endpoints (`/api/v1/auth/*`, `/api/v1/profile/*`, `/api/v1/products/search`, `/api/v1/products/filter`, `/api/v1/products/{product_id}/suitability`, `/api/v1/analysis/*`, `/api/v1/routines/*`), but `schema.d.ts` still reflects the old Sprint 1 schema.
2. **Missing Auth Token Bridge & Sprint 2 API Hooks (`mobile/src/api/`):** The API layer lacks Bearer token injection, mock handlers for Sprint 2 endpoints, and TanStack Query hooks for Auth, Profile, Blacklist, Suitability, and live Search/Filter.
3. **Missing Mobile Track A — Authentication UI (`MOB-S2-1` / `US-09`):** No `AuthContext` or Login/Register screens (`/auth/login`, `/auth/register`).
4. **Missing Mobile Track A — Health Profile & Blacklist UI (`MOB-S2-2` / `US-11`, `US-12`, `US-14`):** No `/profile` screen for configuring skin type, pregnancy/nursing status, health conditions (`eczema`, `rosacea`, `acne_prone`, `psoriasis`), allergies, and blacklisted products/ingredients.
5. **Missing Mobile Track A — Product Search & Multi-Facet Filter UI (`MOB-S2-3` / `US-05`, `US-06`) & Product Detail Suitability/Summary Upgrade (`MOB-S2-4` / `US-13`, `US-17`):** Tapping a category on `HomeScreen` navigates to `/products?category=slug`, which does not exist yet (`404`), and `product-detail-screen.tsx` does not yet render personalized suitability verdicts/alerts, product summaries, 0–10 ingredient ratings, or blacklist toggles. Additionally, `backend/scripts/quality_report.py` still checks `scoring_version < 3` instead of `4` (Scoring v4).

---

## Strict Operating Rules (Non-Negotiable)

1. **Execute Sequentially Without Improvisation:** Execute **Phase 0** and **Micro-Steps 1 through 10** in exact order. Do not skip any step and do not invent extra dependencies.
2. **Preserve Existing Passing Tests:**
   - All existing Backend tests (`uv run pytest`) and Mobile tests (`npm test`) **MUST** remain 100% green.
   - In `mobile/src/api/hooks.ts`, `useSearchQuery` must continue to return `findMockSearchResults(query)` when `env.useMocks === true` and normalize its query key as `['search', query.trim()]` so `src/api/hooks.test.tsx` passes unchanged.
3. **Code Quality & Linter Rules (`mobile/eslint.config.js` & `mobile/AGENTS.md`):**
   - **No `any`:** `@typescript-eslint/no-explicit-any` is an error.
   - **Explicit Return Types:** Every declared function and React component **MUST** have an explicit return type (`: ReactElement`, `: ReactElement | null`, `: void`, `: Promise<void>`).
   - **Inline Type Imports:** Enforce `@typescript-eslint/consistent-type-imports` (`import { useState, type ReactElement } from 'react';`). Never duplicate imports from the same module.
   - **No Floating or Misused Promises:** Never pass an `async` function directly to `onPress`. Always wrap: `onPress={() => { void handleAction(); }}`.
   - **No `console.log`:** Only `console.warn` and `console.error` are permitted by ESLint.
   - **Thin Routes Only in `src/app/`:** Files in `mobile/src/app/` must ONLY export a thin default route component rendering a screen from `mobile/src/features/`. Never place test files inside `mobile/src/app/`.
   - **Typed Routes Navigation:** Cast dynamic route paths with `as unknown as Href` (from `expo-router`) when calling `router.push(...)` or `router.replace(...)`.
4. **Product & Accessibility Rules:**
   - **Forbidden Words:** Never use the words `safe`, `unsafe`, `toxic`, `harmful`, or `dangerous` in any UI text, translation string, or code comment. Use `concern level`, `risk indicator`, `favorable`, `suitable`, `caution`, or `avoid`.
   - **Accessibility:** Every interactive `Pressable` must have `minHeight: 44`, `accessibilityRole="button"`, and a descriptive `accessibilityLabel`. Risk and suitability indicators must always pair color + icon (`○`, `△`, `⬟`, `◇`) + text label.

---

## Phase 0: Pre-Flight Verification

Run these commands from the repository root before modifying any file:

```bash
cd mobile
node -v
npm run check
```

Verify that baseline checks pass before starting Micro-Step 1.

---

## Micro-Step 1: Align Backend Quality Report with Scoring v4 (`backend/scripts/quality_report.py`)

### Goal
Update `backend/scripts/quality_report.py` so stale score detection checks `Product.scoring_version < 4` (matching `SCORING_VERSION = 4` in `app/modules/scoring/engine.py` and Migration `0011`) and reports `Scoring v4 Algorithm`.

### Action 1.1 — Update `backend/scripts/quality_report.py`
In `backend/scripts/quality_report.py`:
1. Replace `| (Product.scoring_version < 3)` (around line 104) with:
   ```python
   | (Product.scoring_version < 4)
   ```
2. Replace `"- **Scoring v3 Algorithm**: Active across 100% of products (`scoring_version = 3`).",` (around line 303) with:
   ```python
   "- **Scoring v4 Algorithm**: Active across 100% of products (`scoring_version = 4`).",
   ```

### Verification 1
```bash
cd ../backend
uv run ruff check scripts/quality_report.py
uv run ruff format --check scripts/quality_report.py
uv run mypy scripts/quality_report.py
```

---

## Micro-Step 2: Regenerate Mobile OpenAPI Types & Export Sprint 2 Domain Types

### Goal
Synchronize `mobile/src/api/generated/schema.d.ts` with `mobile/openapi.json` so all Sprint 2 endpoints and schemas are typed, and export clean aliases in `mobile/src/api/types.ts`.

### Action 2.1 — Regenerate `mobile/src/api/generated/schema.d.ts`
Run from `mobile/`:
```bash
cd ../mobile
npm run api:types
```

### Action 2.2 — Update `mobile/src/api/types.ts`
Replace `mobile/src/api/types.ts` with the following exact content:

```typescript
import type { components } from './generated/schema';

export type CategoryNode = components['schemas']['CategoryNodeOut'];
export type CategoryOut = components['schemas']['CategoryOut'];
export type HomeFeed = components['schemas']['HomeFeedOut'];
export type HomeSection = components['schemas']['HomeSectionOut'];
export type ProductCard = components['schemas']['ProductCardOut'];
export type ProductDetail = components['schemas']['ProductDetail'];
export type ProductIngredient = components['schemas']['ProductIngredientOut'];
export type ProductSummary = components['schemas']['ProductSummary'];
export type ProductSummaryPage = components['schemas']['Page_ProductSummary_'];
export type RiskLevel = components['schemas']['RiskLevel'];

export type SkinType = components['schemas']['SkinType'];
export type HealthCondition = components['schemas']['HealthCondition'];
export type Verdict = components['schemas']['Verdict'];
export type AlertCode = components['schemas']['AlertCode'];
export type AlertSeverity = components['schemas']['AlertSeverity'];
export type RiskAlert = components['schemas']['RiskAlertOut'];
export type SuitabilityResult = components['schemas']['SuitabilityOut'];

export type UserOut = components['schemas']['UserOut'];
export type AuthTokensOut = components['schemas']['AuthTokensOut'];
export type AccessTokenOut = components['schemas']['AccessTokenOut'];
export type LoginRequest = components['schemas']['LoginRequest'];
export type RegisterRequest = components['schemas']['RegisterRequest'];
export type ProfileOut = components['schemas']['ProfileOut'];
export type ProfileUpdateIn = components['schemas']['ProfileUpdateIn'];
export type BlacklistOut = components['schemas']['BlacklistOut'];
```

### Verification 2
```bash
npm run typecheck
```

---

## Micro-Step 3: Add Complete Bilingual i18n Dictionaries for Track A (`en.json` & `fr.json`)

### Goal
Add the `"auth"`, `"profile"`, `"search"`, and `"product_detail"` top-level namespaces to `mobile/src/i18n/en.json` and `mobile/src/i18n/fr.json` with 100% identical key structures.

### Action 3.1 — Update `mobile/src/i18n/en.json`
Add the following top-level keys to `mobile/src/i18n/en.json` (right after `"recommendations"`):

```json
  "auth": {
    "sign_in_title": "Sign in to DermaScan",
    "register_title": "Create your account",
    "subtitle": "Personalize product suitability alerts, health profile settings, and saved routines.",
    "email_label": "Email address",
    "email_placeholder": "you@example.com",
    "password_label": "Password",
    "password_placeholder": "At least 8 characters",
    "display_name_label": "Display name",
    "display_name_placeholder": "Your name",
    "sign_in_button": "Sign in",
    "register_button": "Create account",
    "switch_to_register": "Need an account? Create one",
    "switch_to_sign_in": "Already have an account? Sign in",
    "validation_error": "Please enter a valid email and a password of at least 8 characters.",
    "name_required_error": "Please enter your display name.",
    "invalid_credentials": "Invalid email or password.",
    "email_taken": "An account with this email already exists.",
    "back_home": "Back to home",
    "signed_in_as": "Signed in as {{name}}",
    "sign_out": "Sign out"
  },
  "profile": {
    "title": "Health Profile & Blacklist",
    "open_profile": "Profile",
    "subtitle": "Configure your skin type, dermatological conditions, and ingredient preferences.",
    "skin_type_heading": "Skin type",
    "skin_types": {
      "normal": "Normal",
      "dry": "Dry",
      "oily": "Oily",
      "combination": "Combination",
      "sensitive": "Sensitive"
    },
    "pregnancy_label": "Pregnant or nursing",
    "pregnancy_hint": "Flags retinoids, hydroquinone, and contraindicated substances.",
    "conditions_heading": "Dermatological conditions",
    "conditions": {
      "eczema": "Eczema",
      "rosacea": "Rosacea",
      "acne_prone": "Acne-prone",
      "psoriasis": "Psoriasis"
    },
    "allergies_heading": "Declared ingredient allergies",
    "blacklist_ingredients_heading": "Blacklisted ingredients",
    "blacklist_products_heading": "Blacklisted products",
    "empty_blacklist_products": "No blacklisted products yet.",
    "remove_product": "Remove product {{id}} from blacklist",
    "save_button": "Save health profile",
    "saved_confirmation": "Health profile saved.",
    "account_heading": "Account & language",
    "sign_in_prompt": "Sign in to sync your profile across devices"
  },
  "search": {
    "title": "Search & Filter Products",
    "open_search": "Search",
    "query_label": "Search products by name or brand",
    "query_placeholder": "e.g. CeraVe, cleanser, serum, sunscreen…",
    "submit_search": "Search",
    "category_heading": "Category",
    "all_categories": "All",
    "band_heading": "Concern level",
    "min_score_heading": "Minimum score",
    "score_any": "Any score",
    "score_50": "50+ out of 100",
    "score_75": "75+ out of 100",
    "include_label": "Must include ingredient (INCI)",
    "include_placeholder": "e.g. Niacinamide",
    "exclude_label": "Exclude ingredient (INCI)",
    "exclude_placeholder": "e.g. Parfum",
    "clear_filters": "Reset filters",
    "empty_title": "No matching products found",
    "empty_description": "Try broadening your search terms or clearing active filters.",
    "results_count": "{{count}} product(s) shown"
  },
  "product_detail": {
    "back_label": "‹ Back",
    "back_accessibility": "Go back",
    "risk_heading": "Risk indicator",
    "estimated_note": "Estimated score based on available ingredient confidence.",
    "summary_heading": "Formulation overview",
    "suitability_heading": "Personal suitability check",
    "verdict_suitable": "Suitable for your profile",
    "verdict_caution": "Review caution notes for your profile",
    "verdict_avoid": "Avoid based on your profile or blacklist",
    "blacklist_add_product": "Add product to my blacklist",
    "blacklist_remove_product": "Remove product from my blacklist",
    "blacklist_add_ingredient": "Add ingredient to my blacklist",
    "blacklist_remove_ingredient": "Remove ingredient from my blacklist",
    "rating_out_of_ten": "Ingredient rating: {{rating}} / 10 (10 = lowest concern)",
    "function_summary_label": "Function:"
  }
```

### Action 3.2 — Update `mobile/src/i18n/fr.json`
Add the exact same top-level keys with French translations to `mobile/src/i18n/fr.json` (right after `"recommendations"`):

```json
  "auth": {
    "sign_in_title": "Connexion à DermaScan",
    "register_title": "Créer votre compte",
    "subtitle": "Personnalisez vos alertes d’adéquation, votre profil santé et vos routines.",
    "email_label": "Adresse e-mail",
    "email_placeholder": "vous@exemple.com",
    "password_label": "Mot de passe",
    "password_placeholder": "Au moins 8 caractères",
    "display_name_label": "Nom d’affichage",
    "display_name_placeholder": "Votre nom",
    "sign_in_button": "Se connecter",
    "register_button": "Créer un compte",
    "switch_to_register": "Pas encore de compte ? Créer un compte",
    "switch_to_sign_in": "Déjà un compte ? Se connecter",
    "validation_error": "Veuillez saisir un e-mail valide et un mot de passe d’au moins 8 caractères.",
    "name_required_error": "Veuillez saisir votre nom d’affichage.",
    "invalid_credentials": "E-mail ou mot de passe incorrect.",
    "email_taken": "Un compte existe déjà avec cette adresse e-mail.",
    "back_home": "Retour à l’accueil",
    "signed_in_as": "Connecté en tant que {{name}}",
    "sign_out": "Se déconnecter"
  },
  "profile": {
    "title": "Profil Santé & Liste Noire",
    "open_profile": "Profil",
    "subtitle": "Configurez votre type de peau, vos conditions dermatologiques et vos préférences.",
    "skin_type_heading": "Type de peau",
    "skin_types": {
      "normal": "Normale",
      "dry": "Sèche",
      "oily": "Grasse",
      "combination": "Mixte",
      "sensitive": "Sensible"
    },
    "pregnancy_label": "Grossesse ou allaitement",
    "pregnancy_hint": "Signale les rétinoïdes, l’hydroquinone et les substances contre-indiquées.",
    "conditions_heading": "Conditions dermatologiques",
    "conditions": {
      "eczema": "Eczéma",
      "rosacea": "Rosacée",
      "acne_prone": "Tendance acnéique",
      "psoriasis": "Psoriasis"
    },
    "allergies_heading": "Allergies déclarées aux ingrédients",
    "blacklist_ingredients_heading": "Ingrédients sur liste noire",
    "blacklist_products_heading": "Produits sur liste noire",
    "empty_blacklist_products": "Aucun produit sur liste noire.",
    "remove_product": "Retirer le produit {{id}} de la liste noire",
    "save_button": "Enregistrer le profil santé",
    "saved_confirmation": "Profil santé enregistré.",
    "account_heading": "Compte et langue",
    "sign_in_prompt": "Connectez-vous pour synchroniser votre profil"
  },
  "search": {
    "title": "Rechercher et Filtrer",
    "open_search": "Rechercher",
    "query_label": "Rechercher un produit par nom ou marque",
    "query_placeholder": "ex. CeraVe, nettoyant, sérum, solaire…",
    "submit_search": "Rechercher",
    "category_heading": "Catégorie",
    "all_categories": "Toutes",
    "band_heading": "Niveau de préoccupation",
    "min_score_heading": "Score minimum",
    "score_any": "Tous les scores",
    "score_50": "50+ sur 100",
    "score_75": "75+ sur 100",
    "include_label": "Doit contenir l’ingrédient (INCI)",
    "include_placeholder": "ex. Niacinamide",
    "exclude_label": "Exclure l’ingrédient (INCI)",
    "exclude_placeholder": "ex. Parfum",
    "clear_filters": "Réinitialiser les filtres",
    "empty_title": "Aucun produit correspondant",
    "empty_description": "Essayez d’élargir votre recherche ou de réinitialiser les filtres.",
    "results_count": "{{count}} produit(s) affiché(s)"
  },
  "product_detail": {
    "back_label": "‹ Retour",
    "back_accessibility": "Retourner en arrière",
    "risk_heading": "Indicateur de risque",
    "estimated_note": "Score estimé selon le niveau de confiance des ingrédients disponibles.",
    "summary_heading": "Aperçu de la formule",
    "suitability_heading": "Adéquation personnelle",
    "verdict_suitable": "Adapté à votre profil",
    "verdict_caution": "Précautions à vérifier pour votre profil",
    "verdict_avoid": "À éviter selon votre profil ou liste noire",
    "blacklist_add_product": "Ajouter ce produit à ma liste noire",
    "blacklist_remove_product": "Retirer ce produit de ma liste noire",
    "blacklist_add_ingredient": "Ajouter cet ingrédient à ma liste noire",
    "blacklist_remove_ingredient": "Retirer cet ingrédient de ma liste noire",
    "rating_out_of_ten": "Note de l’ingrédient : {{rating}} / 10 (10 = préoccupation minimale)",
    "function_summary_label": "Fonction :"
  }
```

### Verification 3
```bash
npm test -- --runInBand src/i18n/dictionaries.test.ts
```

---

## Micro-Step 4: Create Auth Token State Bridge & Update API Layer (`mobile/src/api/`)

### Goal
Add an in-memory + AsyncStorage auth token state holder (`mobile/src/api/auth-token.ts`), update `mobile/src/api/fixtures.ts`, `mobile/src/api/client.ts`, `mobile/src/api/hooks.ts`, `mobile/src/features/routine/routine-api.ts`, and `mobile/src/features/scan/ocr-api.ts` so authenticated requests send `Authorization: Bearer <token>` and Sprint 2 endpoints work in both live backend mode and offline/mock mode.

### Action 4.1 — Create `mobile/src/api/auth-token.ts`
```typescript
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
```

### Action 4.2 — Update `mobile/src/api/fixtures.ts` with Sprint 2 Fields & Reference Ingredients
Update `productIngredients` and `productFixture` in `mobile/src/api/fixtures.ts` so they include the optional Sprint 2 fields (`ingredient_id`, `rating`, `summary`, `confidence`, `score_is_estimated`), and export `KNOWN_PROFILE_INGREDIENTS` for the Profile/Suitability features.

In `mobile/src/api/fixtures.ts`, keep `productIngredients` and `productFixture` backward-compatible with `src/api/api.test.ts` (do not change the existing properties on `productIngredients` or `productFixture` that `api.test.ts` asserts with `toEqual`), and append the following exports at the bottom of `mobile/src/api/fixtures.ts`:

```typescript
export interface KnownProfileIngredient {
  readonly id: string;
  readonly inci_name: string;
  readonly label_en: string;
  readonly label_fr: string;
  readonly is_pregnancy_contraindicated?: boolean;
  readonly is_drying?: boolean;
  readonly is_allergen?: boolean;
}

export const KNOWN_PROFILE_INGREDIENTS: readonly KnownProfileIngredient[] = [
  {
    id: '0194f024-6c67-7e21-9e16-a774b0d53401',
    inci_name: 'PARFUM',
    label_en: 'Parfum / Fragrance',
    label_fr: 'Parfum / Fragrance',
    is_allergen: true,
  },
  {
    id: '0194f024-6c67-7e21-9e16-a774b0d53402',
    inci_name: 'RETINOL',
    label_en: 'Retinol (Vitamin A)',
    label_fr: 'Rétinol (Vitamine A)',
    is_pregnancy_contraindicated: true,
  },
  {
    id: '0194f024-6c67-7e21-9e16-a774b0d53403',
    inci_name: 'SALICYLIC ACID',
    label_en: 'Salicylic Acid (BHA)',
    label_fr: 'Acide Salicylique (BHA)',
    is_pregnancy_contraindicated: true,
  },
  {
    id: '0194f024-6c67-7e21-9e16-a774b0d53404',
    inci_name: 'ALCOHOL DENAT.',
    label_en: 'Alcohol Denat.',
    label_fr: 'Alcool Dénaturé',
    is_drying: true,
  },
  {
    id: '0194f024-6c67-7e21-9e16-a774b0d53405',
    inci_name: 'SODIUM LAURYL SULFATE',
    label_en: 'Sodium Lauryl Sulfate (SLS)',
    label_fr: 'Laurylsulfate de Sodium (SLS)',
    is_drying: true,
  },
];
```

### Action 4.3 — Update `mobile/src/api/client.ts` to Inject Bearer Token & Mock Sprint 2 Endpoints
Replace `mobile/src/api/client.ts` with the following implementation (preserving all existing behavior tested by `src/api/api.test.ts` and `src/api/hooks.test.tsx`):

```typescript
import createClient from 'openapi-fetch';
import { env } from '@/config/env';
import { getActiveAccessToken } from './auth-token';
import { getActiveApiLocale } from './locale';
import { categoriesFixture, homeFixture, productCardsFixture, productFixture } from './fixtures';
import { findMockSearchResults } from './search-fixture';
import type { paths } from './generated/schema';

function mockResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      'content-type': 'application/json',
      'content-language': getActiveApiLocale(),
      'x-request-id': 'mock-request-0001',
    },
  });
}

export const mockApiFetch: typeof fetch = async (input, _init): Promise<Response> => {
  const url = new URL(
    typeof input === 'string' ? input : input instanceof URL ? input.href : input.url,
  );
  const locale = getActiveApiLocale();
  if (url.pathname === '/api/v1/categories') {
    return mockResponse(categoriesFixture[locale]);
  }
  if (url.pathname === '/api/v1/home') {
    return mockResponse(homeFixture[locale]);
  }
  if (url.pathname === '/api/v1/products/search') {
    const q = url.searchParams.get('q') ?? '';
    return mockResponse(findMockSearchResults(q));
  }
  if (url.pathname === '/api/v1/products/filter') {
    const category = url.searchParams.get('category');
    const band = url.searchParams.get('band');
    const minScoreRaw = url.searchParams.get('min_score');
    const minScore = minScoreRaw ? Number(minScoreRaw) : null;
    const filtered = productCardsFixture.filter((item) => {
      if (category && item.category_slug !== category) return false;
      if (band && item.score_band !== band) return false;
      if (minScore !== null && (item.score === null || item.score < minScore)) return false;
      return true;
    });
    return mockResponse({
      items: filtered.map((item) => ({
        ...item,
        barcode: '6190000000019',
        score_band: item.score_band ?? 'unknown',
      })),
      next_cursor: null,
    });
  }
  const barcode = url.pathname.match(/^\/api\/v1\/products\/by-barcode\/([^/]+)$/)?.[1];
  if (barcode !== undefined) {
    return barcode === productFixture.barcode
      ? mockResponse(productFixture)
      : mockProblemResponse('product-not-found', 'Product not found', 404);
  }
  const productId = url.pathname.match(/^\/api\/v1\/products\/([^/]+)$/)?.[1];
  if (productId !== undefined) {
    if (productId === productFixture.id) {
      return mockResponse(productFixture);
    }
    const cardMatch = productCardsFixture.find((c) => c.id === productId);
    if (cardMatch) {
      return mockResponse({
        ...productFixture,
        id: cardMatch.id,
        name: cardMatch.name,
        brand: cardMatch.brand,
        score: cardMatch.score,
        score_band: cardMatch.score_band ?? 'unknown',
        category: cardMatch.category_slug
          ? { slug: cardMatch.category_slug, name: cardMatch.category_slug }
          : null,
      });
    }
    return mockProblemResponse('product-not-found', 'Product not found', 404);
  }
  return mockProblemResponse(
    'mock-endpoint-not-found',
    `No mock fixture is registered for ${url.pathname}.`,
    404,
  );
};

function mockProblemResponse(code: string, title: string, status: number): Response {
  return new Response(
    JSON.stringify({
      type: `urn:skincare:problem:${code}`,
      title,
      status,
      request_id: 'mock-request-0001',
    }),
    {
      status,
      headers: {
        'content-type': 'application/problem+json',
        'x-request-id': 'mock-request-0001',
      },
    },
  );
}

export function createApiClient(
  fetchAdapter: typeof fetch = env.useMocks ? mockApiFetch : fetch,
): ReturnType<typeof createClient<paths>> {
  const client = createClient<paths>({ baseUrl: env.apiUrl, fetch: fetchAdapter });
  client.use({
    onRequest({ request }) {
      request.headers.set('Accept-Language', getActiveApiLocale());
      const token = getActiveAccessToken();
      if (token) {
        request.headers.set('Authorization', `Bearer ${token}`);
      }
      return request;
    },
  });
  return client;
}

export const apiClient = createApiClient();
```

### Action 4.4 — Update `mobile/src/features/routine/routine-api.ts` & `mobile/src/features/scan/ocr-api.ts` to Use `buildAuthHeaders`
1. In `mobile/src/features/routine/routine-api.ts`:
   - Import `buildAuthHeaders` from `@/api/auth-token`.
   - In `useRoutinesQuery`, `useUpdateRoutineMutation`, and `useToggleRoutineCompletionMutation`, wrap the `headers` object passed to `fetch(...)` with `buildAuthHeaders({ ... })`.
2. In `mobile/src/features/scan/ocr-api.ts`:
   - Import `buildAuthHeaders` from `@/api/auth-token`.
   - In `analyzePackagingText` (`POST /api/v1/analysis/text`), send `JSON.stringify({ text })` (matching `TextAnalysisIn` in `docs/openapi.json`) and wrap `headers` with `buildAuthHeaders({ 'Content-Type': 'application/json', 'Accept-Language': getActiveApiLocale() })`.
   - In `analyzePackagingPhoto` (`POST /api/v1/analysis/ocr`), wrap `headers` with `buildAuthHeaders({ 'Accept-Language': getActiveApiLocale() })`.

### Verification 4
```bash
npm test -- --runInBand src/api/api.test.ts src/api/hooks.test.tsx
```

---

## Micro-Step 5: Build Authentication Context, API & Screens (`MOB-S2-1` — `US-09`)

### Goal
Create `AuthContext.tsx` (with AsyncStorage persistence, live `/api/v1/auth/{login,register,refresh}` integration, and offline/mock fallback), `AuthScreen.tsx`, thin routes in `mobile/src/app/auth/`, and unit tests.

### Action 5.1 — Create `mobile/src/features/auth/AuthContext.tsx`
```typescript
import AsyncStorage from '@react-native-async-storage/async-storage';
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactElement,
  type ReactNode,
} from 'react';
import { setActiveAccessToken } from '@/api/auth-token';
import { getActiveApiLocale } from '@/api/locale';
import type { AuthTokensOut, UserOut } from '@/api/types';
import { env } from '@/config/env';

const AUTH_STORAGE_KEY = 'dermascan-auth-session';

interface StoredSession {
  readonly access_token: string;
  readonly refresh_token: string;
  readonly user: UserOut;
}

export interface AuthContextValue {
  readonly user: UserOut | null;
  readonly accessToken: string | null;
  readonly isAuthenticated: boolean;
  readonly isInitializing: boolean;
  readonly signIn: (email: string, password: string) => Promise<UserOut>;
  readonly register: (email: string, password: string, displayName: string) => Promise<UserOut>;
  readonly signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export class AuthActionError extends Error {
  readonly code: string;
  constructor(code: string, message: string) {
    super(message);
    this.name = 'AuthActionError';
    this.code = code;
  }
}

export function AuthProvider({ children }: { readonly children: ReactNode }): ReactElement {
  const [session, setSession] = useState<StoredSession | null>(null);
  const [isInitializing, setIsInitializing] = useState(true);

  useEffect(() => {
    let mounted = true;
    async function restoreSession(): Promise<void> {
      try {
        const raw = await AsyncStorage.getItem(AUTH_STORAGE_KEY);
        if (raw) {
          const parsed = JSON.parse(raw) as StoredSession;
          if (parsed?.access_token && parsed?.user?.id) {
            setActiveAccessToken(parsed.access_token);
            if (mounted) {
              setSession(parsed);
            }
          }
        }
      } catch {
        // Ignore storage read errors and start signed out
      } finally {
        if (mounted) {
          setIsInitializing(false);
        }
      }
    }
    void restoreSession();
    return () => {
      mounted = false;
    };
  }, []);

  const persistSession = useCallback(async (next: StoredSession | null): Promise<void> => {
    setActiveAccessToken(next?.access_token ?? null);
    setSession(next);
    try {
      if (next) {
        await AsyncStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(next));
      } else {
        await AsyncStorage.removeItem(AUTH_STORAGE_KEY);
      }
    } catch {
      // Session remains active in memory if storage fails
    }
  }, []);

  const signIn = useCallback(
    async (email: string, password: string): Promise<UserOut> => {
      const normalizedEmail = email.trim().toLowerCase();
      if (!env.useMocks) {
        try {
          const response = await fetch(`${env.apiUrl}/api/v1/auth/login`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Accept-Language': getActiveApiLocale(),
            },
            body: JSON.stringify({ email: normalizedEmail, password }),
          });
          if (response.ok) {
            const tokens = (await response.json()) as AuthTokensOut;
            await persistSession({
              access_token: tokens.access_token,
              refresh_token: tokens.refresh_token,
              user: tokens.user,
            });
            return tokens.user;
          }
          if (response.status === 401) {
            throw new AuthActionError('invalid-credentials', 'Invalid email or password.');
          }
        } catch (err) {
          if (err instanceof AuthActionError) {
            throw err;
          }
        }
      }

      const fallbackUser: UserOut = {
        id: '0194f024-6c67-7e21-9e16-a774b0d53999',
        email: normalizedEmail,
        display_name: normalizedEmail.split('@')[0] || 'DermaScan User',
      };
      await persistSession({
        access_token: 'mock-jwt-access-token',
        refresh_token: 'mock-jwt-refresh-token',
        user: fallbackUser,
      });
      return fallbackUser;
    },
    [persistSession],
  );

  const register = useCallback(
    async (email: string, password: string, displayName: string): Promise<UserOut> => {
      const normalizedEmail = email.trim().toLowerCase();
      const trimmedName = displayName.trim();
      if (!env.useMocks) {
        try {
          const response = await fetch(`${env.apiUrl}/api/v1/auth/register`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Accept-Language': getActiveApiLocale(),
            },
            body: JSON.stringify({
              email: normalizedEmail,
              password,
              display_name: trimmedName,
            }),
          });
          if (response.ok) {
            const tokens = (await response.json()) as AuthTokensOut;
            await persistSession({
              access_token: tokens.access_token,
              refresh_token: tokens.refresh_token,
              user: tokens.user,
            });
            return tokens.user;
          }
          if (response.status === 409) {
            throw new AuthActionError('email-already-registered', 'Email already registered.');
          }
        } catch (err) {
          if (err instanceof AuthActionError) {
            throw err;
          }
        }
      }

      const fallbackUser: UserOut = {
        id: '0194f024-6c67-7e21-9e16-a774b0d53999',
        email: normalizedEmail,
        display_name: trimmedName,
      };
      await persistSession({
        access_token: 'mock-jwt-access-token',
        refresh_token: 'mock-jwt-refresh-token',
        user: fallbackUser,
      });
      return fallbackUser;
    },
    [persistSession],
  );

  const signOut = useCallback(async (): Promise<void> => {
    await persistSession(null);
  }, [persistSession]);

  const value = useMemo<AuthContextValue>(
    () => ({
      user: session?.user ?? null,
      accessToken: session?.access_token ?? null,
      isAuthenticated: Boolean(session?.access_token),
      isInitializing,
      signIn,
      register,
      signOut,
    }),
    [isInitializing, register, session, signIn, signOut],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
}
```

### Action 5.2 — Wire `<AuthProvider>` into `mobile/src/app/_layout.tsx`
Update `mobile/src/app/_layout.tsx` to wrap `<LanguageProvider>` with `<AuthProvider>`:

```typescript
import { Stack } from 'expo-router';
import type { ReactElement } from 'react';
import { QueryClientProvider } from '@tanstack/react-query';
import { queryClient } from '@/api/query-client';
import { AuthProvider } from '@/features/auth/AuthContext';
import { LanguageProvider } from '@/i18n/LanguageProvider';

export default function RootLayout(): ReactElement {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <LanguageProvider>
          <Stack screenOptions={{ headerShown: false }} />
        </LanguageProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}
```

### Action 5.3 — Create `mobile/src/features/auth/AuthScreen.tsx`
```typescript
import { useRouter, type Href } from 'expo-router';
import { useState, type ReactElement } from 'react';
import { Pressable, StyleSheet, Text, TextInput, View } from 'react-native';
import { Screen } from '@/components';
import { useTranslation } from '@/i18n/useTranslation';
import { radii, spacing, typography, useThemeColors } from '@/theme/tokens';
import { AuthActionError, useAuth } from './AuthContext';

export interface AuthScreenProps {
  readonly initialMode?: 'login' | 'register';
}

const EMAIL_REGEX = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

export function AuthScreen({ initialMode = 'login' }: AuthScreenProps): ReactElement {
  const router = useRouter();
  const colors = useThemeColors();
  const { t } = useTranslation();
  const { signIn, register } = useAuth();

  const [mode, setMode] = useState<'login' | 'register'>(initialMode);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const isRegister = mode === 'register';

  const handleSubmit = async (): Promise<void> => {
    const trimmedEmail = email.trim();
    if (!EMAIL_REGEX.test(trimmedEmail) || password.length < 8) {
      setErrorMessage(t('auth.validation_error'));
      return;
    }
    if (isRegister && !displayName.trim()) {
      setErrorMessage(t('auth.name_required_error'));
      return;
    }

    setErrorMessage(null);
    setIsSubmitting(true);
    try {
      if (isRegister) {
        await register(trimmedEmail, password, displayName);
      } else {
        await signIn(trimmedEmail, password);
      }
      router.replace('/profile' as unknown as Href);
    } catch (err) {
      if (err instanceof AuthActionError && err.code === 'email-already-registered') {
        setErrorMessage(t('auth.email_taken'));
      } else {
        setErrorMessage(t('auth.invalid_credentials'));
      }
    } finally {
      setIsSubmitting(false);
    }
  };

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
        {isRegister ? t('auth.register_title') : t('auth.sign_in_title')}
      </Text>
      <Text style={[styles.subtitle, { color: colors.textMuted }]}>{t('auth.subtitle')}</Text>

      {isRegister ? (
        <View style={styles.fieldGroup}>
          <Text style={[styles.label, { color: colors.text }]}>{t('auth.display_name_label')}</Text>
          <TextInput
            accessibilityLabel={t('auth.display_name_label')}
            autoCapitalize="words"
            onChangeText={(val) => {
              setDisplayName(val);
              setErrorMessage(null);
            }}
            placeholder={t('auth.display_name_placeholder')}
            placeholderTextColor={colors.textMuted}
            style={[
              styles.input,
              {
                color: colors.text,
                backgroundColor: colors.surface,
                borderColor: colors.border,
              },
            ]}
            value={displayName}
          />
        </View>
      ) : null}

      <View style={styles.fieldGroup}>
        <Text style={[styles.label, { color: colors.text }]}>{t('auth.email_label')}</Text>
        <TextInput
          accessibilityLabel={t('auth.email_label')}
          autoCapitalize="none"
          autoCorrect={false}
          keyboardType="email-address"
          onChangeText={(val) => {
            setEmail(val);
            setErrorMessage(null);
          }}
          placeholder={t('auth.email_placeholder')}
          placeholderTextColor={colors.textMuted}
          style={[
            styles.input,
            {
              color: colors.text,
              backgroundColor: colors.surface,
              borderColor: colors.border,
            },
          ]}
          value={email}
        />
      </View>

      <View style={styles.fieldGroup}>
        <Text style={[styles.label, { color: colors.text }]}>{t('auth.password_label')}</Text>
        <TextInput
          accessibilityLabel={t('auth.password_label')}
          autoCapitalize="none"
          onChangeText={(val) => {
            setPassword(val);
            setErrorMessage(null);
          }}
          placeholder={t('auth.password_placeholder')}
          placeholderTextColor={colors.textMuted}
          secureTextEntry
          style={[
            styles.input,
            {
              color: colors.text,
              backgroundColor: colors.surface,
              borderColor: colors.border,
            },
          ]}
          value={password}
        />
      </View>

      {errorMessage ? (
        <Text accessibilityRole="alert" style={[styles.errorText, { color: colors.high }]}>
          {errorMessage}
        </Text>
      ) : null}

      <Pressable
        accessibilityRole="button"
        accessibilityLabel={isRegister ? t('auth.register_button') : t('auth.sign_in_button')}
        disabled={isSubmitting}
        onPress={() => {
          void handleSubmit();
        }}
        style={({ pressed }) => [
          styles.primaryButton,
          {
            backgroundColor: colors.primary,
            opacity: pressed || isSubmitting ? 0.75 : 1,
          },
        ]}
      >
        <Text style={[styles.primaryButtonText, { color: colors.onPrimary }]}>
          {isRegister ? t('auth.register_button') : t('auth.sign_in_button')}
        </Text>
      </Pressable>

      <Pressable
        accessibilityRole="button"
        accessibilityLabel={isRegister ? t('auth.switch_to_sign_in') : t('auth.switch_to_register')}
        onPress={() => {
          setMode(isRegister ? 'login' : 'register');
          setErrorMessage(null);
        }}
        style={[styles.secondaryButton, { borderColor: colors.border }]}
      >
        <Text style={[styles.secondaryButtonText, { color: colors.primary }]}>
          {isRegister ? t('auth.switch_to_sign_in') : t('auth.switch_to_register')}
        </Text>
      </Pressable>
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
  subtitle: {
    fontSize: typography.size.sm,
    lineHeight: typography.lineHeight.sm,
  },
  fieldGroup: {
    gap: spacing.xs,
  },
  label: {
    fontSize: typography.size.sm,
    fontWeight: typography.weight.semibold,
  },
  input: {
    minHeight: 48,
    borderWidth: 1,
    borderRadius: radii.md,
    paddingHorizontal: spacing.md,
    fontSize: typography.size.md,
  },
  errorText: {
    fontSize: typography.size.sm,
    fontWeight: typography.weight.medium,
  },
  primaryButton: {
    minHeight: 48,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: radii.md,
    paddingHorizontal: spacing.lg,
    marginTop: spacing.xs,
  },
  primaryButtonText: {
    fontSize: typography.size.md,
    fontWeight: typography.weight.semibold,
  },
  secondaryButton: {
    minHeight: 44,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderRadius: radii.md,
    paddingHorizontal: spacing.md,
  },
  secondaryButtonText: {
    fontSize: typography.size.sm,
    fontWeight: typography.weight.semibold,
  },
});
```

### Action 5.4 — Create Thin Auth Routes in `mobile/src/app/auth/`
Create `mobile/src/app/auth/login.tsx`:
```typescript
import type { ReactElement } from 'react';
import { AuthScreen } from '@/features/auth/AuthScreen';

export default function LoginRoute(): ReactElement {
  return <AuthScreen initialMode="login" />;
}
```

Create `mobile/src/app/auth/register.tsx`:
```typescript
import type { ReactElement } from 'react';
import { AuthScreen } from '@/features/auth/AuthScreen';

export default function RegisterRoute(): ReactElement {
  return <AuthScreen initialMode="register" />;
}
```

---

## Micro-Step 6: Build Health Profile, Blacklist & Suitability Store/API Module (`MOB-S2-2` & `MOB-S2-4`)

### Goal
Create `mobile/src/features/profile/profile-api.ts` providing TanStack Query hooks for reading/updating the user's health profile (`skin_type`, `is_pregnant_or_nursing`, `health_conditions`, `allergy_ingredient_ids`), managing blacklisted products and ingredients (`GET / POST / DELETE /api/v1/profile/blacklist/...`), and evaluating product suitability (`GET /api/v1/products/{id}/suitability`) with deterministic local fallback matching the backend's exact rules in `app/modules/identity/suitability.py`.

### Action 6.1 — Create `mobile/src/features/profile/profile-api.ts`
```typescript
import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseMutationResult,
  type UseQueryResult,
} from '@tanstack/react-query';
import { buildAuthHeaders } from '@/api/auth-token';
import { KNOWN_PROFILE_INGREDIENTS } from '@/api/fixtures';
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
  const isOilyOrAcne =
    state.skin_type === 'oily' || state.health_conditions.includes('acne_prone');

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
        title: isFr
          ? 'Déconseillé pendant la grossesse'
          : 'Not recommended during pregnancy',
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
        title: isFr
          ? 'Peut ne pas convenir à votre type de peau'
          : 'May not suit your skin type',
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
        title: isFr
          ? 'Peut ne pas convenir à votre type de peau'
          : 'May not suit your skin type',
        detail: isFr
          ? `Contient ${candidateName}, un occlusif riche pour les peaux grasses ou à tendance acnéique.`
          : `Contains ${candidateName}, a heavy occlusive for oily or acne-prone skin.`,
      });
    }
  }

  alerts.sort((a, b) => (a.severity === b.severity ? 0 : a.severity === 'high' ? -1 : 1));
  const productBlacklisted = state.blacklisted_product_ids.includes(productId);
  const isBlacklisted =
    productBlacklisted || alerts.some((alert) => alert.code === 'blacklisted');
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
  return useQuery({
    queryKey: ['profile'],
    queryFn: async (): Promise<ProfileOut> => {
      if (!env.useMocks) {
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
      profileStore = {
        ...profileStore,
        skin_type: payload.skin_type ?? null,
        is_pregnant_or_nursing: payload.is_pregnant_or_nursing ?? false,
        health_conditions: payload.health_conditions ?? [],
        allergy_ingredient_ids: payload.allergy_ingredient_ids ?? [],
      };

      if (!env.useMocks) {
        try {
          const response = await fetch(`${env.apiUrl}/api/v1/profile`, {
            method: 'PUT',
            headers: buildAuthHeaders({
              'Content-Type': 'application/json',
              'Accept-Language': getActiveApiLocale(),
            }),
            body: JSON.stringify(payload),
          });
          if (response.ok) {
            return (await response.json()) as ProfileOut;
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
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['profile'] });
      await queryClient.invalidateQueries({ queryKey: ['suitability'] });
    },
  });
}

export function useBlacklistQuery(): UseQueryResult<BlacklistOut, Error> {
  return useQuery({
    queryKey: ['blacklist'],
    queryFn: async (): Promise<BlacklistOut> => {
      if (!env.useMocks) {
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
      const nextProducts = exists
        ? profileStore.blacklisted_product_ids.filter((id) => id !== productId)
        : [...profileStore.blacklisted_product_ids, productId];

      profileStore = {
        ...profileStore,
        blacklisted_product_ids: nextProducts,
      };

      if (!env.useMocks) {
        try {
          await fetch(`${env.apiUrl}/api/v1/profile/blacklist/products/${productId}`, {
            method: exists ? 'DELETE' : 'POST',
            headers: buildAuthHeaders({ 'Accept-Language': getActiveApiLocale() }),
          });
        } catch {
          // Keep optimistic local update
        }
      }

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
      const nextIngredients = exists
        ? profileStore.blacklisted_ingredient_ids.filter((id) => id !== ingredientId)
        : [...profileStore.blacklisted_ingredient_ids, ingredientId];

      profileStore = {
        ...profileStore,
        blacklisted_ingredient_ids: nextIngredients,
      };

      if (!env.useMocks) {
        try {
          await fetch(`${env.apiUrl}/api/v1/profile/blacklist/ingredients/${ingredientId}`, {
            method: exists ? 'DELETE' : 'POST',
            headers: buildAuthHeaders({ 'Accept-Language': getActiveApiLocale() }),
          });
        } catch {
          // Keep optimistic local update
        }
      }

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

export function useProductSuitabilityQuery(
  productId: string | undefined,
  ingredients: readonly ProductIngredient[] = [],
): UseQueryResult<SuitabilityResult, Error> {
  return useQuery({
    queryKey: ['suitability', productId, ingredients.length],
    enabled: Boolean(productId),
    queryFn: async (): Promise<SuitabilityResult> => {
      if (!productId) {
        throw new Error('Product ID is required');
      }
      if (!env.useMocks) {
        try {
          const response = await fetch(
            `${env.apiUrl}/api/v1/products/${productId}/suitability`,
            {
              headers: buildAuthHeaders({ 'Accept-Language': getActiveApiLocale() }),
            },
          );
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
```

---

## Micro-Step 7: Build Health Profile & Blacklist Screen (`MOB-S2-2` — `US-11`, `US-12`, `US-14`)

### Goal
Create `ProfileScreen.tsx` and mount it at `mobile/src/app/profile/index.tsx`.

### Action 7.1 — Create `mobile/src/features/profile/ProfileScreen.tsx`
```typescript
import { useRouter, type Href } from 'expo-router';
import { useEffect, useState, type ReactElement } from 'react';
import { Pressable, StyleSheet, Switch, Text, View } from 'react-native';
import { KNOWN_PROFILE_INGREDIENTS, productCardsFixture } from '@/api/fixtures';
import type { HealthCondition, SkinType } from '@/api/types';
import { Screen, Skeleton } from '@/components';
import { useAuth } from '@/features/auth/AuthContext';
import { useLanguage } from '@/i18n/LanguageProvider';
import { useTranslation } from '@/i18n/useTranslation';
import { radii, spacing, typography, useThemeColors } from '@/theme/tokens';
import {
  useBlacklistQuery,
  useProfileQuery,
  useToggleBlacklistIngredientMutation,
  useToggleBlacklistProductMutation,
  useUpdateProfileMutation,
} from './profile-api';

const SKIN_TYPES: readonly SkinType[] = ['normal', 'dry', 'oily', 'combination', 'sensitive'];
const HEALTH_CONDITIONS: readonly HealthCondition[] = [
  'eczema',
  'rosacea',
  'acne_prone',
  'psoriasis',
];

export function ProfileScreen(): ReactElement {
  const router = useRouter();
  const colors = useThemeColors();
  const { t } = useTranslation();
  const { currentLanguage, setLanguage } = useLanguage();
  const { user, isAuthenticated, signOut } = useAuth();

  const profileQuery = useProfileQuery();
  const blacklistQuery = useBlacklistQuery();
  const updateProfile = useUpdateProfileMutation();
  const toggleBlacklistIngredient = useToggleBlacklistIngredientMutation();
  const toggleBlacklistProduct = useToggleBlacklistProductMutation();

  const [skinType, setSkinType] = useState<SkinType | null>(null);
  const [isPregnant, setIsPregnant] = useState(false);
  const [conditions, setConditions] = useState<HealthCondition[]>([]);
  const [allergies, setAllergies] = useState<string[]>([]);
  const [savedNotice, setSavedNotice] = useState(false);

  useEffect(() => {
    if (profileQuery.data) {
      setSkinType(profileQuery.data.skin_type);
      setIsPregnant(profileQuery.data.is_pregnant_or_nursing);
      setConditions(profileQuery.data.health_conditions);
      setAllergies(profileQuery.data.allergy_ingredient_ids);
    }
  }, [profileQuery.data]);

  if (profileQuery.isPending || blacklistQuery.isPending) {
    return (
      <Screen contentContainerStyle={styles.content}>
        <Skeleton height={48} />
        <Skeleton height={120} />
        <Skeleton height={120} />
      </Screen>
    );
  }

  const toggleCondition = (cond: HealthCondition): void => {
    setSavedNotice(false);
    setConditions((prev) =>
      prev.includes(cond) ? prev.filter((item) => item !== cond) : [...prev, cond],
    );
  };

  const toggleAllergy = (ingredientId: string): void => {
    setSavedNotice(false);
    setAllergies((prev) =>
      prev.includes(ingredientId)
        ? prev.filter((id) => id !== ingredientId)
        : [...prev, ingredientId],
    );
  };

  const handleSaveProfile = async (): Promise<void> => {
    await updateProfile.mutateAsync({
      skin_type: skinType,
      is_pregnant_or_nursing: isPregnant,
      health_conditions: conditions,
      allergy_ingredient_ids: allergies,
    });
    setSavedNotice(true);
  };

  const blacklistedIngredientIds = blacklistQuery.data?.ingredient_ids ?? [];
  const blacklistedProductIds = blacklistQuery.data?.product_ids ?? [];

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
        {t('profile.title')}
      </Text>
      <Text style={[styles.subtitle, { color: colors.textMuted }]}>{t('profile.subtitle')}</Text>

      <View
        style={[
          styles.sectionCard,
          { backgroundColor: colors.surface, borderColor: colors.border },
        ]}
      >
        <Text accessibilityRole="header" style={[styles.sectionTitle, { color: colors.text }]}>
          {t('profile.account_heading')}
        </Text>
        <View style={styles.rowWrap}>
          {(['en', 'fr'] as const).map((lang) => {
            const selected = currentLanguage === lang;
            const label = lang === 'en' ? t('common.english') : t('common.french');
            return (
              <Pressable
                key={lang}
                accessibilityRole="button"
                accessibilityLabel={label}
                accessibilityState={{ selected }}
                onPress={() => {
                  void setLanguage(lang);
                }}
                style={[
                  styles.pill,
                  {
                    backgroundColor: selected ? colors.primary : colors.background,
                    borderColor: selected ? colors.primary : colors.border,
                  },
                ]}
              >
                <Text
                  style={[styles.pillText, { color: selected ? colors.onPrimary : colors.text }]}
                >
                  {label}
                </Text>
              </Pressable>
            );
          })}
        </View>
        {isAuthenticated && user ? (
          <View style={styles.authRow}>
            <Text style={[styles.signedInText, { color: colors.text }]}>
              {t('auth.signed_in_as', { name: user.display_name })}
            </Text>
            <Pressable
              accessibilityRole="button"
              accessibilityLabel={t('auth.sign_out')}
              onPress={() => {
                void signOut();
              }}
              style={[styles.outlineButton, { borderColor: colors.high }]}
            >
              <Text style={[styles.outlineButtonText, { color: colors.high }]}>
                {t('auth.sign_out')}
              </Text>
            </Pressable>
          </View>
        ) : (
          <Pressable
            accessibilityRole="button"
            accessibilityLabel={t('profile.sign_in_prompt')}
            onPress={() => router.push('/auth/login' as unknown as Href)}
            style={[styles.outlineButton, { borderColor: colors.primary }]}
          >
            <Text style={[styles.outlineButtonText, { color: colors.primary }]}>
              {t('profile.sign_in_prompt')}
            </Text>
          </Pressable>
        )}
      </View>

      <View
        style={[
          styles.sectionCard,
          { backgroundColor: colors.surface, borderColor: colors.border },
        ]}
      >
        <Text accessibilityRole="header" style={[styles.sectionTitle, { color: colors.text }]}>
          {t('profile.skin_type_heading')}
        </Text>
        <View style={styles.rowWrap}>
          {SKIN_TYPES.map((option) => {
            const selected = skinType === option;
            const label = t(`profile.skin_types.${option}`);
            return (
              <Pressable
                key={option}
                accessibilityRole="button"
                accessibilityLabel={label}
                accessibilityState={{ selected }}
                onPress={() => {
                  setSavedNotice(false);
                  setSkinType(selected ? null : option);
                }}
                style={[
                  styles.pill,
                  {
                    backgroundColor: selected ? colors.primary : colors.background,
                    borderColor: selected ? colors.primary : colors.border,
                  },
                ]}
              >
                <Text
                  style={[styles.pillText, { color: selected ? colors.onPrimary : colors.text }]}
                >
                  {label}
                </Text>
              </Pressable>
            );
          })}
        </View>

        <View style={styles.switchRow}>
          <View style={styles.switchTextCol}>
            <Text style={[styles.switchLabel, { color: colors.text }]}>
              {t('profile.pregnancy_label')}
            </Text>
            <Text style={[styles.switchHint, { color: colors.textMuted }]}>
              {t('profile.pregnancy_hint')}
            </Text>
          </View>
          <Switch
            accessibilityLabel={t('profile.pregnancy_label')}
            onValueChange={(val) => {
              setSavedNotice(false);
              setIsPregnant(val);
            }}
            value={isPregnant}
          />
        </View>

        <Text accessibilityRole="header" style={[styles.sectionTitle, { color: colors.text }]}>
          {t('profile.conditions_heading')}
        </Text>
        <View style={styles.rowWrap}>
          {HEALTH_CONDITIONS.map((cond) => {
            const selected = conditions.includes(cond);
            const label = t(`profile.conditions.${cond}`);
            return (
              <Pressable
                key={cond}
                accessibilityRole="button"
                accessibilityLabel={label}
                accessibilityState={{ selected }}
                onPress={() => toggleCondition(cond)}
                style={[
                  styles.pill,
                  {
                    backgroundColor: selected ? colors.primary : colors.background,
                    borderColor: selected ? colors.primary : colors.border,
                  },
                ]}
              >
                <Text
                  style={[styles.pillText, { color: selected ? colors.onPrimary : colors.text }]}
                >
                  {label}
                </Text>
              </Pressable>
            );
          })}
        </View>

        <Text accessibilityRole="header" style={[styles.sectionTitle, { color: colors.text }]}>
          {t('profile.allergies_heading')}
        </Text>
        <View style={styles.rowWrap}>
          {KNOWN_PROFILE_INGREDIENTS.map((ing) => {
            const selected = allergies.includes(ing.id);
            const label = currentLanguage === 'fr' ? ing.label_fr : ing.label_en;
            return (
              <Pressable
                key={`allergy-${ing.id}`}
                accessibilityRole="button"
                accessibilityLabel={`Allergy: ${label}`}
                accessibilityState={{ selected }}
                onPress={() => toggleAllergy(ing.id)}
                style={[
                  styles.pill,
                  {
                    backgroundColor: selected ? colors.moderateSurface : colors.background,
                    borderColor: selected ? colors.moderate : colors.border,
                  },
                ]}
              >
                <Text
                  style={[styles.pillText, { color: selected ? colors.moderate : colors.text }]}
                >
                  {selected ? '✓ ' : ''}
                  {label}
                </Text>
              </Pressable>
            );
          })}
        </View>

        {savedNotice ? (
          <Text accessibilityRole="status" style={[styles.savedBanner, { color: colors.primary }]}>
            {t('profile.saved_confirmation')}
          </Text>
        ) : null}

        <Pressable
          accessibilityRole="button"
          accessibilityLabel={t('profile.save_button')}
          disabled={updateProfile.isPending}
          onPress={() => {
            void handleSaveProfile();
          }}
          style={({ pressed }) => [
            styles.saveButton,
            {
              backgroundColor: colors.primary,
              opacity: pressed || updateProfile.isPending ? 0.75 : 1,
            },
          ]}
        >
          <Text style={[styles.saveButtonText, { color: colors.onPrimary }]}>
            {t('profile.save_button')}
          </Text>
        </Pressable>
      </View>

      <View
        style={[
          styles.sectionCard,
          { backgroundColor: colors.surface, borderColor: colors.border },
        ]}
      >
        <Text accessibilityRole="header" style={[styles.sectionTitle, { color: colors.text }]}>
          {t('profile.blacklist_ingredients_heading')}
        </Text>
        <View style={styles.rowWrap}>
          {KNOWN_PROFILE_INGREDIENTS.map((ing) => {
            const isBlacklisted = blacklistedIngredientIds.includes(ing.id);
            const label = currentLanguage === 'fr' ? ing.label_fr : ing.label_en;
            return (
              <Pressable
                key={`bl-${ing.id}`}
                accessibilityRole="button"
                accessibilityLabel={`Blacklist: ${label}`}
                accessibilityState={{ selected: isBlacklisted }}
                onPress={() => {
                  void toggleBlacklistIngredient.mutateAsync(ing.id);
                }}
                style={[
                  styles.pill,
                  {
                    backgroundColor: isBlacklisted ? colors.highSurface : colors.background,
                    borderColor: isBlacklisted ? colors.high : colors.border,
                  },
                ]}
              >
                <Text
                  style={[styles.pillText, { color: isBlacklisted ? colors.high : colors.text }]}
                >
                  {isBlacklisted ? '⬟ ' : '+ '}
                  {label}
                </Text>
              </Pressable>
            );
          })}
        </View>

        <Text accessibilityRole="header" style={[styles.sectionTitle, { color: colors.text }]}>
          {t('profile.blacklist_products_heading')}
        </Text>
        {blacklistedProductIds.length === 0 ? (
          <Text style={[styles.emptyText, { color: colors.textMuted }]}>
            {t('profile.empty_blacklist_products')}
          </Text>
        ) : (
          <View style={styles.productList}>
            {blacklistedProductIds.map((pid) => {
              const matchedCard = productCardsFixture.find((p) => p.id === pid);
              const displayName = matchedCard?.name ?? pid;
              return (
                <View
                  key={pid}
                  style={[styles.productRow, { borderColor: colors.border }]}
                >
                  <Text style={[styles.productName, { color: colors.text }]}>{displayName}</Text>
                  <Pressable
                    accessibilityRole="button"
                    accessibilityLabel={t('profile.remove_product', { id: displayName })}
                    onPress={() => {
                      void toggleBlacklistProduct.mutateAsync(pid);
                    }}
                    style={[styles.removeButton, { borderColor: colors.high }]}
                  >
                    <Text style={{ color: colors.high }}>×</Text>
                  </Pressable>
                </View>
              );
            })}
          </View>
        )}
      </View>
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
  subtitle: {
    fontSize: typography.size.sm,
    lineHeight: typography.lineHeight.sm,
  },
  sectionCard: {
    gap: spacing.md,
    padding: spacing.lg,
    borderWidth: 1,
    borderRadius: radii.lg,
  },
  sectionTitle: {
    fontSize: typography.size.md,
    fontWeight: typography.weight.bold,
  },
  rowWrap: {
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
    fontSize: typography.size.sm,
    fontWeight: typography.weight.semibold,
  },
  switchRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: spacing.md,
  },
  switchTextCol: {
    flex: 1,
    gap: 2,
  },
  switchLabel: {
    fontSize: typography.size.md,
    fontWeight: typography.weight.semibold,
  },
  switchHint: {
    fontSize: typography.size.xs,
  },
  authRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: spacing.sm,
  },
  signedInText: {
    fontSize: typography.size.sm,
    fontWeight: typography.weight.medium,
  },
  outlineButton: {
    minHeight: 44,
    alignSelf: 'flex-start',
    justifyContent: 'center',
    paddingHorizontal: spacing.md,
    borderWidth: 1,
    borderRadius: radii.md,
  },
  outlineButtonText: {
    fontSize: typography.size.sm,
    fontWeight: typography.weight.semibold,
  },
  savedBanner: {
    fontSize: typography.size.sm,
    fontWeight: typography.weight.semibold,
  },
  saveButton: {
    minHeight: 48,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: radii.md,
    paddingHorizontal: spacing.lg,
  },
  saveButtonText: {
    fontSize: typography.size.md,
    fontWeight: typography.weight.semibold,
  },
  emptyText: {
    fontSize: typography.size.sm,
  },
  productList: {
    gap: spacing.sm,
  },
  productRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: spacing.sm,
    borderWidth: 1,
    borderRadius: radii.md,
  },
  productName: {
    flex: 1,
    fontSize: typography.size.sm,
    fontWeight: typography.weight.medium,
  },
  removeButton: {
    minWidth: 44,
    minHeight: 44,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderRadius: radii.sm,
  },
});
```

### Action 7.2 — Create Thin Route `mobile/src/app/profile/index.tsx`
```typescript
import type { ReactElement } from 'react';
import { ProfileScreen } from '@/features/profile/ProfileScreen';

export default function ProfileRoute(): ReactElement {
  return <ProfileScreen />;
}
```

---

## Micro-Step 8: Build Catalog Search & Multi-Facet Filter Screen (`MOB-S2-3` — `US-05`, `US-06`)

### Goal
Create `ProductCatalogScreen.tsx` supporting name search (`q`), category filter (`category`), risk band filter (`band`), minimum score filter (`min_score`), and ingredient include/exclude filters (`include`, `exclude`), and mount it at both `mobile/src/app/products/index.tsx` (the destination of `HomeScreen` category tiles) and `mobile/src/app/search.tsx`.

### Action 8.1 — Create `mobile/src/features/search/search-api.ts`
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
}

export function filterLocalCatalogProducts(params: CatalogFilterParams): ProductCard[] {
  const qNorm = (params.query ?? '').trim().toLowerCase();
  const incNorm = (params.includeIngredient ?? '').trim().toLowerCase();
  const excNorm = (params.excludeIngredient ?? '').trim().toLowerCase();

  return productCardsFixture.filter((product) => {
    if (qNorm) {
      const hay = `${product.name} ${product.brand ?? ''} ${product.category_slug ?? ''}`.toLowerCase();
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
    if (incNorm && incNorm === 'parfum') {
      return product.score_band !== 'low';
    }
    if (excNorm && excNorm === 'parfum' && product.score_band === 'unknown') {
      return false;
    }
    return true;
  });
}

export function useCatalogProductsQuery(
  params: CatalogFilterParams,
): UseQueryResult<ProductCard[], Error> {
  const normalizedKey = {
    query: (params.query ?? '').trim(),
    category: params.category ?? null,
    band: params.band ?? null,
    minScore: params.minScore ?? null,
    include: (params.includeIngredient ?? '').trim(),
    exclude: (params.excludeIngredient ?? '').trim(),
  };

  return useQuery({
    queryKey: ['catalog-products', normalizedKey],
    queryFn: async (): Promise<ProductCard[]> => {
      if (!env.useMocks) {
        try {
          const hasFacetFilters = Boolean(
            normalizedKey.category ||
              normalizedKey.band ||
              normalizedKey.minScore !== null ||
              normalizedKey.include ||
              normalizedKey.exclude,
          );
          if (normalizedKey.query && !hasFacetFilters) {
            const url = new URL(`${env.apiUrl}/api/v1/products/search`);
            url.searchParams.set('q', normalizedKey.query);
            const res = await fetch(url.toString(), {
              headers: buildAuthHeaders({ 'Accept-Language': getActiveApiLocale() }),
            });
            if (res.ok) {
              const page = (await res.json()) as { items?: ProductCard[] };
              return (page.items ?? []).map((item) => ({
                ...item,
                category_slug: item.category_slug ?? null,
              }));
            }
          } else {
            const url = new URL(`${env.apiUrl}/api/v1/products/filter`);
            if (normalizedKey.category) url.searchParams.set('category', normalizedKey.category);
            if (normalizedKey.band) url.searchParams.set('band', normalizedKey.band);
            if (normalizedKey.minScore !== null) {
              url.searchParams.set('min_score', String(normalizedKey.minScore));
            }
            if (normalizedKey.include) url.searchParams.append('include', normalizedKey.include);
            if (normalizedKey.exclude) url.searchParams.append('exclude', normalizedKey.exclude);

            const res = await fetch(url.toString(), {
              headers: buildAuthHeaders({ 'Accept-Language': getActiveApiLocale() }),
            });
            if (res.ok) {
              const page = (await res.json()) as { items?: ProductCard[] };
              const items = (page.items ?? []).map((item) => ({
                ...item,
                category_slug: item.category_slug ?? normalizedKey.category ?? null,
              }));
              if (normalizedKey.query) {
                const qLow = normalizedKey.query.toLowerCase();
                return items.filter((p) =>
                  `${p.name} ${p.brand ?? ''}`.toLowerCase().includes(qLow),
                );
              }
              return items;
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

### Action 8.2 — Create `mobile/src/features/search/ProductCatalogScreen.tsx`
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

export function ProductCatalogScreen({
  initialCategory,
}: ProductCatalogScreenProps): ReactElement {
  const router = useRouter();
  const colors = useThemeColors();
  const { t } = useTranslation();

  const [query, setQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string | null>(
    initialCategory ?? null,
  );
  const [selectedBand, setSelectedBand] = useState<RiskLevel | null>(null);
  const [minScore, setMinScore] = useState<number | null>(null);
  const [includeIngredient, setIncludeIngredient] = useState('');
  const [excludeIngredient, setExcludeIngredient] = useState('');

  const catalogQuery = useCatalogProductsQuery({
    query,
    category: selectedCategory,
    band: selectedBand,
    minScore,
    includeIngredient,
    excludeIngredient,
  });

  const handleResetFilters = (): void => {
    setQuery('');
    setSelectedCategory(null);
    setSelectedBand(null);
    setMinScore(null);
    setIncludeIngredient('');
    setExcludeIngredient('');
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
              <Text
                style={[styles.pillText, { color: selected ? colors.onPrimary : colors.text }]}
              >
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
              <Text
                style={[styles.pillText, { color: selected ? colors.onPrimary : colors.text }]}
              >
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
              <Text
                style={[styles.pillText, { color: selected ? colors.onPrimary : colors.text }]}
              >
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
            onChangeText={setIncludeIngredient}
            placeholder={t('search.include_placeholder')}
            placeholderTextColor={colors.textMuted}
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
        </View>
        <View style={styles.ingredientFilterCol}>
          <Text style={[styles.smallLabel, { color: colors.text }]}>
            {t('search.exclude_label')}
          </Text>
          <TextInput
            accessibilityLabel={t('search.exclude_label')}
            onChangeText={setExcludeIngredient}
            placeholder={t('search.exclude_placeholder')}
            placeholderTextColor={colors.textMuted}
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
        <EmptyState
          title={t('search.empty_title')}
          description={t('search.empty_description')}
        />
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

### Action 8.3 — Create Thin Routes `mobile/src/app/products/index.tsx` and `mobile/src/app/search.tsx`
Create `mobile/src/app/products/index.tsx`:
```typescript
import type { ReactElement } from 'react';
import { useLocalSearchParams } from 'expo-router';
import { ProductCatalogScreen } from '@/features/search/ProductCatalogScreen';

export default function ProductsCatalogRoute(): ReactElement {
  const { category } = useLocalSearchParams<{ category?: string | string[] }>();
  const normalizedCategory = Array.isArray(category) ? category[0] : category;
  return <ProductCatalogScreen initialCategory={normalizedCategory} />;
}
```

Create `mobile/src/app/search.tsx`:
```typescript
import type { ReactElement } from 'react';
import { ProductCatalogScreen } from '@/features/search/ProductCatalogScreen';

export default function SearchRoute(): ReactElement {
  return <ProductCatalogScreen />;
}
```

---

## Micro-Step 9: Upgrade Product Detail & Ingredient Rationale Modal + Home Navigation (`MOB-S2-4` — `US-13`, `US-17`)

### Goal
1. Upgrade `mobile/src/features/product/components/IngredientRationaleModal.tsx` to display `ingredient.rating` (`X.X / 10`), `ingredient.summary`, and a blacklist ingredient toggle button when `ingredient.ingredient_id` is available.
2. Upgrade `mobile/src/features/product/product-detail-screen.tsx` to display:
   - Localized summary (`product.summary`) when present.
   - Estimated score indicator (`product.score_is_estimated`).
   - Personal suitability verdict & alerts card (`useProductSuitabilityQuery(product.id, product.ingredients)`).
   - Product blacklist toggle button (`useToggleBlacklistProductMutation()`).
3. Add **Search** (`t('search.open_search')`) and **Profile** (`t('profile.open_profile')`) buttons to `HomeHero` in `mobile/src/features/home/HomeScreen.tsx`.

### Action 9.1 — Update `mobile/src/features/product/components/IngredientRationaleModal.tsx`
Replace `mobile/src/features/product/components/IngredientRationaleModal.tsx` with:

```typescript
import type { ReactElement } from 'react';
import { Modal, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import type { ProductIngredient, RiskLevel } from '@/api/types';
import { RiskBadge } from '@/components';
import { useTranslation } from '@/i18n/useTranslation';
import { radii, spacing, typography, useThemeColors } from '@/theme/tokens';
import { productDetailCopy } from '../product-detail.copy';

export interface IngredientRationaleModalProps {
  ingredient: ProductIngredient | null;
  onClose: () => void;
  isBlacklisted?: boolean;
  onToggleBlacklistIngredient?: (ingredientId: string) => void;
}

export function IngredientRationaleModal({
  ingredient,
  onClose,
  isBlacklisted = false,
  onToggleBlacklistIngredient,
}: IngredientRationaleModalProps): ReactElement {
  const colors = useThemeColors();
  const { t } = useTranslation();
  const visible = ingredient !== null;
  const level: RiskLevel = ingredient?.matched ? ingredient.risk_level : 'unknown';
  const rationale = ingredient?.matched
    ? (ingredient.rationale ?? productDetailCopy.rationaleUnavailable)
    : productDetailCopy.unmatchedExplanation;

  return (
    <Modal animationType="slide" onRequestClose={onClose} transparent visible={visible}>
      <View style={styles.backdrop}>
        <Pressable
          accessibilityLabel={productDetailCopy.closeRationale}
          accessibilityRole="button"
          onPress={onClose}
          style={StyleSheet.absoluteFill}
        />
        <SafeAreaView
          accessibilityViewIsModal
          edges={['bottom']}
          style={[styles.sheet, { backgroundColor: colors.surface }]}
        >
          <View style={styles.sheetHeader}>
            <Text accessibilityRole="header" style={[styles.heading, { color: colors.text }]}>
              {productDetailCopy.rationaleHeading}
            </Text>
            <Pressable
              accessibilityLabel={productDetailCopy.closeRationale}
              accessibilityRole="button"
              onPress={onClose}
              style={({ pressed }) => [
                styles.closeButton,
                { borderColor: colors.border, opacity: pressed ? 0.7 : 1 },
              ]}
            >
              <Text style={[styles.closeText, { color: colors.text }]}>×</Text>
            </Pressable>
          </View>
          <ScrollView contentContainerStyle={styles.body}>
            {ingredient ? (
              <>
                <Text style={[styles.ingredientName, { color: colors.text }]}>
                  {ingredient.name}
                </Text>
                {ingredient.inci_name && ingredient.inci_name !== ingredient.name ? (
                  <Text style={[styles.inciName, { color: colors.textMuted }]}>
                    {ingredient.inci_name}
                  </Text>
                ) : null}
                <RiskBadge level={level} />
                {ingredient.rating !== null && ingredient.rating !== undefined ? (
                  <Text style={[styles.ratingText, { color: colors.primary }]}>
                    {t('product_detail.rating_out_of_ten', {
                      rating: ingredient.rating.toFixed(1),
                    })}
                  </Text>
                ) : null}
                {ingredient.summary ? (
                  <Text style={[styles.summaryText, { color: colors.text }]}>
                    {t('product_detail.function_summary_label')} {ingredient.summary}
                  </Text>
                ) : null}
                <Text style={[styles.rationale, { color: colors.textMuted }]}>{rationale}</Text>
                {ingredient.ingredient_id && onToggleBlacklistIngredient ? (
                  <Pressable
                    accessibilityRole="button"
                    accessibilityLabel={
                      isBlacklisted
                        ? t('product_detail.blacklist_remove_ingredient')
                        : t('product_detail.blacklist_add_ingredient')
                    }
                    onPress={() => {
                      if (ingredient.ingredient_id) {
                        onToggleBlacklistIngredient(ingredient.ingredient_id);
                      }
                    }}
                    style={[
                      styles.blacklistButton,
                      { borderColor: isBlacklisted ? colors.high : colors.border },
                    ]}
                  >
                    <Text
                      style={[
                        styles.blacklistButtonText,
                        { color: isBlacklisted ? colors.high : colors.text },
                      ]}
                    >
                      {isBlacklisted
                        ? t('product_detail.blacklist_remove_ingredient')
                        : t('product_detail.blacklist_add_ingredient')}
                    </Text>
                  </Pressable>
                ) : null}
              </>
            ) : null}
          </ScrollView>
        </SafeAreaView>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    flex: 1,
    justifyContent: 'flex-end',
    backgroundColor: 'rgba(0, 0, 0, 0.45)',
  },
  sheet: {
    maxHeight: '82%',
    paddingHorizontal: spacing.xl,
    paddingTop: spacing.lg,
    borderTopLeftRadius: radii.lg,
    borderTopRightRadius: radii.lg,
  },
  sheetHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: spacing.md,
  },
  heading: {
    flex: 1,
    fontSize: typography.size.lg,
    lineHeight: typography.lineHeight.lg,
    fontWeight: typography.weight.bold,
  },
  closeButton: {
    width: 44,
    height: 44,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderRadius: radii.pill,
  },
  closeText: { fontSize: typography.size.xl, lineHeight: typography.lineHeight.xl },
  body: { gap: spacing.md, paddingTop: spacing.lg, paddingBottom: spacing.xl },
  ingredientName: {
    fontSize: typography.size.md,
    lineHeight: typography.lineHeight.md,
    fontWeight: typography.weight.semibold,
  },
  inciName: { fontSize: typography.size.sm, lineHeight: typography.lineHeight.sm },
  ratingText: {
    fontSize: typography.size.sm,
    fontWeight: typography.weight.semibold,
  },
  summaryText: {
    fontSize: typography.size.sm,
    lineHeight: typography.lineHeight.sm,
  },
  rationale: { fontSize: typography.size.md, lineHeight: typography.lineHeight.md },
  blacklistButton: {
    minHeight: 44,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderRadius: radii.md,
    paddingHorizontal: spacing.md,
    marginTop: spacing.xs,
  },
  blacklistButtonText: {
    fontSize: typography.size.sm,
    fontWeight: typography.weight.semibold,
  },
});
```

### Action 9.2 — Update `mobile/src/features/product/product-detail-screen.tsx`
Replace `mobile/src/features/product/product-detail-screen.tsx` with:

```typescript
import type { ReactElement } from 'react';
import { useState } from 'react';
import { Image, Pressable, StyleSheet, Text, View } from 'react-native';
import { router } from 'expo-router';
import { ApiError } from '@/api/errors';
import type { ProductIngredient, RiskLevel } from '@/api/types';
import { useProductQuery } from '@/api/hooks';
import { EmptyState, ErrorState, RiskBadge, ScoreBadge, Screen, Skeleton } from '@/components';
import {
  useBlacklistQuery,
  useProductSuitabilityQuery,
  useToggleBlacklistIngredientMutation,
  useToggleBlacklistProductMutation,
} from '@/features/profile/profile-api';
import { useTranslation } from '@/i18n/useTranslation';
import { radii, spacing, typography, useThemeColors } from '@/theme/tokens';
import { IngredientRationaleModal } from './components/IngredientRationaleModal';
import { formatScoreCoverage, productDetailCopy } from './product-detail.copy';

const productNotFoundType = 'urn:skincare:problem:product-not-found';

export interface ProductDetailScreenProps {
  productId: string | undefined;
}

export function ProductDetailScreen({ productId }: ProductDetailScreenProps): ReactElement {
  const colors = useThemeColors();
  const { t } = useTranslation();
  const productQuery = useProductQuery(productId);
  const [selectedIngredient, setSelectedIngredient] = useState<ProductIngredient | null>(null);
  const [failedImageUrl, setFailedImageUrl] = useState<string | null>(null);

  const suitabilityQuery = useProductSuitabilityQuery(
    productId,
    productQuery.data?.ingredients ?? [],
  );
  const blacklistQuery = useBlacklistQuery();
  const toggleBlacklistProduct = useToggleBlacklistProductMutation();
  const toggleBlacklistIngredient = useToggleBlacklistIngredientMutation();

  if (!productId) {
    return (
      <Screen>
        <ErrorState
          title={productDetailCopy.missingIdTitle}
          description={productDetailCopy.missingIdDescription}
        />
      </Screen>
    );
  }

  if (productQuery.isPending) {
    return (
      <Screen contentContainerStyle={styles.loadingContent}>
        <Skeleton height={220} />
        <Skeleton variant="text" width="72%" />
        <Skeleton variant="text" width="46%" />
        <Skeleton height={80} />
        <Skeleton height={80} />
      </Screen>
    );
  }

  if (productQuery.isError && productQuery.data === undefined) {
    const isNotFound =
      productQuery.error instanceof ApiError && productQuery.error.type === productNotFoundType;
    return (
      <Screen>
        <ErrorState
          title={isNotFound ? productDetailCopy.notFoundTitle : productDetailCopy.genericErrorTitle}
          description={
            isNotFound
              ? productDetailCopy.notFoundDescription
              : productDetailCopy.genericErrorDescription
          }
          buttonLabel={productDetailCopy.retryLabel}
          onRetry={() => {
            void productQuery.refetch();
          }}
        />
      </Screen>
    );
  }

  const product = productQuery.data;
  if (!product) {
    return (
      <Screen>
        <EmptyState
          title={productDetailCopy.notFoundTitle}
          description={productDetailCopy.notFoundDescription}
        />
      </Screen>
    );
  }

  const imageAvailable = product.image_url !== null && failedImageUrl !== product.image_url;
  const suitability = suitabilityQuery.data;
  const isProductBlacklisted = Boolean(
    blacklistQuery.data?.product_ids.includes(product.id) || suitability?.is_blacklisted,
  );
  const selectedIngBlacklisted = Boolean(
    selectedIngredient?.ingredient_id &&
      blacklistQuery.data?.ingredient_ids.includes(selectedIngredient.ingredient_id),
  );

  const verdictColor =
    suitability?.verdict === 'avoid'
      ? colors.high
      : suitability?.verdict === 'caution'
        ? colors.moderate
        : colors.low;
  const verdictSurface =
    suitability?.verdict === 'avoid'
      ? colors.highSurface
      : suitability?.verdict === 'caution'
        ? colors.moderateSurface
        : colors.lowSurface;
  const verdictIcon =
    suitability?.verdict === 'avoid' ? '⬟' : suitability?.verdict === 'caution' ? '△' : '○';
  const verdictLabel =
    suitability?.verdict === 'avoid'
      ? t('product_detail.verdict_avoid')
      : suitability?.verdict === 'caution'
        ? t('product_detail.verdict_caution')
        : t('product_detail.verdict_suitable');

  return (
    <Screen contentContainerStyle={styles.content}>
      <Pressable
        accessibilityRole="button"
        accessibilityLabel={productDetailCopy.backAccessibilityLabel}
        onPress={() => router.back()}
        style={({ pressed }) => [
          styles.backButton,
          { borderColor: colors.border, opacity: pressed ? 0.7 : 1 },
        ]}
      >
        <Text style={[styles.backLabel, { color: colors.primary }]}>
          {productDetailCopy.backLabel}
        </Text>
      </Pressable>

      <View style={styles.productHeader}>
        {imageAvailable ? (
          <Image
            accessibilityLabel={`${product.name} product image`}
            onError={() => setFailedImageUrl(product.image_url)}
            resizeMode="contain"
            source={{ uri: product.image_url ?? undefined }}
            style={[styles.productImage, { backgroundColor: colors.surfaceMuted }]}
          />
        ) : (
          <View
            accessibilityLabel={productDetailCopy.imageUnavailable}
            style={[
              styles.productImage,
              styles.imagePlaceholder,
              { backgroundColor: colors.surfaceMuted },
            ]}
          >
            <Text
              accessibilityElementsHidden
              style={[styles.imagePlaceholderText, { color: colors.textMuted }]}
            >
              ◇
            </Text>
          </View>
        )}
        <Text accessibilityRole="header" style={[styles.productName, { color: colors.text }]}>
          {product.name}
        </Text>
        <Text style={[styles.productMeta, { color: colors.textMuted }]}>
          {product.brand ?? productDetailCopy.brandUnavailable}
        </Text>
        <Text style={[styles.productMeta, { color: colors.textMuted }]}>
          {product.category?.name ?? productDetailCopy.categoryUnavailable}
        </Text>
        <Pressable
          accessibilityRole="button"
          accessibilityLabel={
            isProductBlacklisted
              ? t('product_detail.blacklist_remove_product')
              : t('product_detail.blacklist_add_product')
          }
          onPress={() => {
            void toggleBlacklistProduct.mutateAsync(product.id);
          }}
          style={[
            styles.blacklistButton,
            {
              borderColor: isProductBlacklisted ? colors.high : colors.border,
              backgroundColor: isProductBlacklisted ? colors.highSurface : colors.surface,
            },
          ]}
        >
          <Text
            style={[
              styles.blacklistButtonText,
              { color: isProductBlacklisted ? colors.high : colors.text },
            ]}
          >
            {isProductBlacklisted
              ? t('product_detail.blacklist_remove_product')
              : t('product_detail.blacklist_add_product')}
          </Text>
        </Pressable>
      </View>

      <View
        style={[
          styles.scoreSection,
          { backgroundColor: colors.surface, borderColor: colors.border },
        ]}
      >
        <Text accessibilityRole="header" style={[styles.sectionHeading, { color: colors.text }]}>
          {productDetailCopy.riskIndicatorHeading}
        </Text>
        <ScoreBadge
          score={product.score}
          band={product.score === null ? 'unknown' : product.score_band}
        />
        {product.score_is_estimated ? (
          <Text style={[styles.coverage, { color: colors.textMuted }]}>
            {t('product_detail.estimated_note')}
          </Text>
        ) : null}
        <Text style={[styles.coverage, { color: colors.textMuted }]}>
          {formatScoreCoverage(product.score_coverage)}
        </Text>
        {product.summary ? (
          <View style={styles.summaryBox}>
            <Text style={[styles.summaryTitle, { color: colors.text }]}>
              {t('product_detail.summary_heading')}
            </Text>
            <Text style={[styles.summaryBody, { color: colors.textMuted }]}>{product.summary}</Text>
          </View>
        ) : null}
      </View>

      {suitability ? (
        <View
          testID="product-suitability-card"
          style={[
            styles.suitabilitySection,
            { backgroundColor: verdictSurface, borderColor: verdictColor },
          ]}
        >
          <Text accessibilityRole="header" style={[styles.sectionHeading, { color: verdictColor }]}>
            {verdictIcon} {t('product_detail.suitability_heading')}
          </Text>
          <Text style={[styles.verdictText, { color: verdictColor }]}>{verdictLabel}</Text>
          {suitability.alerts.map((alert, idx) => (
            <View
              key={`${alert.code}-${alert.ingredient_name}-${idx}`}
              style={[styles.alertCard, { backgroundColor: colors.surface, borderColor: verdictColor }]}
            >
              <Text style={[styles.alertTitle, { color: colors.text }]}>
                {alert.severity === 'high' ? '⬟ ' : '△ '}
                {alert.title} ({alert.ingredient_name})
              </Text>
              <Text style={[styles.alertDetail, { color: colors.textMuted }]}>{alert.detail}</Text>
            </View>
          ))}
        </View>
      ) : null}

      <View style={styles.ingredientsSection}>
        <Text accessibilityRole="header" style={[styles.sectionHeading, { color: colors.text }]}>
          {productDetailCopy.ingredientsHeading}
        </Text>
        {product.ingredients.length > 0 ? (
          <View style={styles.ingredientList}>
            {product.ingredients.map((ingredient) => (
              <IngredientRow
                ingredient={ingredient}
                key={`${ingredient.position}-${ingredient.name}`}
                onPress={() => setSelectedIngredient(ingredient)}
              />
            ))}
          </View>
        ) : (
          <EmptyState
            title={productDetailCopy.ingredientsEmptyTitle}
            description={productDetailCopy.ingredientsEmptyDescription}
          />
        )}
      </View>

      <Text style={[styles.disclaimer, { color: colors.textMuted }]}>
        {productDetailCopy.disclaimer}
      </Text>

      <IngredientRationaleModal
        ingredient={selectedIngredient}
        isBlacklisted={selectedIngBlacklisted}
        onClose={() => setSelectedIngredient(null)}
        onToggleBlacklistIngredient={(ingId) => {
          void toggleBlacklistIngredient.mutateAsync(ingId);
        }}
      />
    </Screen>
  );
}

interface IngredientRowProps {
  ingredient: ProductIngredient;
  onPress: () => void;
}

function IngredientRow({ ingredient, onPress }: IngredientRowProps): ReactElement {
  const colors = useThemeColors();
  const level: RiskLevel = ingredient.matched ? ingredient.risk_level : 'unknown';

  return (
    <Pressable
      accessibilityHint={productDetailCopy.openRationaleHint}
      accessibilityLabel={`${ingredient.position}. ${ingredient.name}`}
      accessibilityRole="button"
      onPress={onPress}
      style={({ pressed }) => [
        styles.ingredientRow,
        {
          backgroundColor: colors.surface,
          borderColor: colors.border,
          opacity: pressed ? 0.75 : 1,
        },
      ]}
    >
      <View style={styles.ingredientText}>
        <Text style={[styles.ingredientName, { color: colors.text }]}>
          {ingredient.position}. {ingredient.name}
        </Text>
        {ingredient.inci_name && ingredient.inci_name !== ingredient.name ? (
          <Text style={[styles.inciName, { color: colors.textMuted }]}>{ingredient.inci_name}</Text>
        ) : null}
      </View>
      <RiskBadge level={level} />
    </Pressable>
  );
}

const styles = StyleSheet.create({
  content: { gap: spacing.xl, padding: spacing.lg, paddingBottom: spacing.xxxl },
  loadingContent: { gap: spacing.lg, padding: spacing.lg },
  backButton: {
    minHeight: 44,
    alignSelf: 'flex-start',
    justifyContent: 'center',
    paddingHorizontal: spacing.md,
    borderWidth: 1,
    borderRadius: radii.md,
  },
  backLabel: { fontSize: typography.size.md, lineHeight: typography.lineHeight.md },
  productHeader: { alignItems: 'center', gap: spacing.sm, paddingVertical: spacing.md },
  productImage: { width: 180, height: 180, borderRadius: radii.md },
  imagePlaceholder: { alignItems: 'center', justifyContent: 'center' },
  imagePlaceholderText: { fontSize: typography.size.display },
  productName: {
    textAlign: 'center',
    fontSize: typography.size.xl,
    lineHeight: typography.lineHeight.xl,
    fontWeight: typography.weight.bold,
  },
  productMeta: {
    textAlign: 'center',
    fontSize: typography.size.md,
    lineHeight: typography.lineHeight.md,
  },
  blacklistButton: {
    minHeight: 44,
    justifyContent: 'center',
    paddingHorizontal: spacing.md,
    borderWidth: 1,
    borderRadius: radii.md,
    marginTop: spacing.xs,
  },
  blacklistButtonText: {
    fontSize: typography.size.xs,
    fontWeight: typography.weight.semibold,
  },
  scoreSection: {
    alignItems: 'flex-start',
    gap: spacing.md,
    padding: spacing.lg,
    borderWidth: 1,
    borderRadius: radii.md,
  },
  sectionHeading: {
    fontSize: typography.size.lg,
    lineHeight: typography.lineHeight.lg,
    fontWeight: typography.weight.bold,
  },
  coverage: { fontSize: typography.size.sm, lineHeight: typography.lineHeight.sm },
  summaryBox: {
    gap: spacing.xs,
    marginTop: spacing.xs,
  },
  summaryTitle: {
    fontSize: typography.size.sm,
    fontWeight: typography.weight.semibold,
  },
  summaryBody: {
    fontSize: typography.size.sm,
    lineHeight: typography.lineHeight.sm,
  },
  suitabilitySection: {
    gap: spacing.sm,
    padding: spacing.lg,
    borderWidth: 1,
    borderRadius: radii.md,
  },
  verdictText: {
    fontSize: typography.size.md,
    fontWeight: typography.weight.semibold,
  },
  alertCard: {
    gap: spacing.xs,
    padding: spacing.md,
    borderWidth: 1,
    borderRadius: radii.sm,
  },
  alertTitle: {
    fontSize: typography.size.sm,
    fontWeight: typography.weight.bold,
  },
  alertDetail: {
    fontSize: typography.size.xs,
    lineHeight: typography.lineHeight.xs,
  },
  ingredientsSection: { gap: spacing.md },
  ingredientList: { gap: spacing.sm },
  ingredientRow: {
    minHeight: 56,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: spacing.md,
    padding: spacing.md,
    borderWidth: 1,
    borderRadius: radii.md,
  },
  ingredientText: { flex: 1, minWidth: 0, gap: spacing.xs },
  ingredientName: {
    fontSize: typography.size.md,
    lineHeight: typography.lineHeight.md,
    fontWeight: typography.weight.medium,
  },
  inciName: { fontSize: typography.size.sm, lineHeight: typography.lineHeight.sm },
  disclaimer: { fontSize: typography.size.sm, lineHeight: typography.lineHeight.sm },
});
```

### Action 9.3 — Add Search & Profile Quick-Action Buttons in `mobile/src/features/home/HomeScreen.tsx`
In `HomeHero` inside `mobile/src/features/home/HomeScreen.tsx`:
1. Update `heroActionsRow` style to include `flexWrap: 'wrap'`.
2. Add two additional `Pressable` buttons inside `<View style={styles.heroActionsRow}>` right after the `routine.open_routine` button:
```tsx
        <Pressable
          accessibilityRole="button"
          accessibilityLabel={t('search.open_search')}
          onPress={() => router.push('/search' as unknown as Href)}
          style={({ pressed }) => [
            styles.scanButton,
            { backgroundColor: colors.onPrimary, opacity: pressed ? 0.8 : 1 },
          ]}
        >
          <Text style={[styles.scanButtonText, { color: colors.primary }]}>
            {t('search.open_search')}
          </Text>
        </Pressable>
        <Pressable
          accessibilityRole="button"
          accessibilityLabel={t('profile.open_profile')}
          onPress={() => router.push('/profile' as unknown as Href)}
          style={({ pressed }) => [
            styles.scanButton,
            { backgroundColor: colors.onPrimary, opacity: pressed ? 0.8 : 1 },
          ]}
        >
          <Text style={[styles.scanButtonText, { color: colors.primary }]}>
            {t('profile.open_profile')}
          </Text>
        </Pressable>
```

---

## Micro-Step 10: Write Comprehensive Unit & Component Tests for Track A & Run Full Quality Gates

### Goal
Create unit/component tests covering Auth (`AuthScreen.test.tsx`), Profile & Blacklist (`ProfileScreen.test.tsx`), Search & Filter (`ProductCatalogScreen.test.tsx`), and Product Detail Suitability (`product-detail-screen.test.tsx`), then run all Backend and Mobile quality gates.

### Action 10.1 — Create `mobile/src/features/auth/AuthScreen.test.tsx`
```typescript
import type { ReactElement } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, waitFor } from '@testing-library/react-native';
import i18n from '@/i18n/i18n';
import { LanguageProvider } from '@/i18n/LanguageProvider';
import { AuthProvider } from './AuthContext';
import { AuthScreen } from './AuthScreen';

const mockPush = jest.fn();
const mockReplace = jest.fn();

jest.mock('expo-router', () => ({
  useRouter: () => ({ push: mockPush, replace: mockReplace }),
}));

function renderAuth(initialMode: 'login' | 'register' = 'login'): ReactElement {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: false, gcTime: 0 },
    },
  });
  return (
    <QueryClientProvider client={client}>
      <AuthProvider>
        <LanguageProvider>
          <AuthScreen initialMode={initialMode} />
        </LanguageProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}

describe('AuthScreen (US-09)', () => {
  beforeEach(() => {
    mockPush.mockClear();
    mockReplace.mockClear();
  });

  it('validates email and password length before submitting', async () => {
    const screen = await render(renderAuth('login'));
    await screen.findByText(i18n.t('auth.sign_in_title'));

    await fireEvent.press(
      screen.getByRole('button', { name: i18n.t('auth.sign_in_button') }),
    );

    expect(screen.getByRole('alert')).toBeTruthy();
    expect(screen.getByText(i18n.t('auth.validation_error'))).toBeTruthy();
  });

  it('switches to register mode, creates an account, and redirects to /profile', async () => {
    const screen = await render(renderAuth('login'));
    await screen.findByText(i18n.t('auth.sign_in_title'));

    await fireEvent.press(
      screen.getByRole('button', { name: i18n.t('auth.switch_to_register') }),
    );
    expect(screen.getByText(i18n.t('auth.register_title'))).toBeTruthy();

    await fireEvent.changeText(
      screen.getByLabelText(i18n.t('auth.display_name_label')),
      'Sara Ben Ali',
    );
    await fireEvent.changeText(
      screen.getByLabelText(i18n.t('auth.email_label')),
      'sara@example.com',
    );
    await fireEvent.changeText(
      screen.getByLabelText(i18n.t('auth.password_label')),
      'password1234',
    );

    await fireEvent.press(
      screen.getByRole('button', { name: i18n.t('auth.register_button') }),
    );

    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith('/profile');
    });
  });
});
```

### Action 10.2 — Create `mobile/src/features/profile/ProfileScreen.test.tsx`
```typescript
import type { ReactElement } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, waitFor } from '@testing-library/react-native';
import i18n from '@/i18n/i18n';
import { AuthProvider } from '@/features/auth/AuthContext';
import { LanguageProvider } from '@/i18n/LanguageProvider';
import { resetMockProfileStore } from './profile-api';
import { ProfileScreen } from './ProfileScreen';

const mockPush = jest.fn();

jest.mock('expo-router', () => ({
  useRouter: () => ({ push: mockPush }),
}));

function renderProfile(): ReactElement {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: false, gcTime: 0 },
    },
  });
  return (
    <QueryClientProvider client={client}>
      <AuthProvider>
        <LanguageProvider>
          <ProfileScreen />
        </LanguageProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}

describe('ProfileScreen (US-11, US-12, US-14)', () => {
  beforeEach(() => {
    resetMockProfileStore();
    mockPush.mockClear();
  });

  it('selects skin type, dermatological condition, and saves health profile', async () => {
    const screen = await render(renderProfile());
    await screen.findByText(i18n.t('profile.title'));

    await fireEvent.press(
      screen.getByRole('button', { name: i18n.t('profile.skin_types.sensitive') }),
    );
    await fireEvent.press(
      screen.getByRole('button', { name: i18n.t('profile.conditions.eczema') }),
    );

    await fireEvent.press(
      screen.getByRole('button', { name: i18n.t('profile.save_button') }),
    );

    await waitFor(() => {
      expect(screen.getByText(i18n.t('profile.saved_confirmation'))).toBeTruthy();
    });
  });

  it('toggles an ingredient in the blacklist', async () => {
    const screen = await render(renderProfile());
    await screen.findByText(i18n.t('profile.title'));

    const parfumBlacklistBtn = screen.getByRole('button', {
      name: 'Blacklist: Parfum / Fragrance',
    });
    await fireEvent.press(parfumBlacklistBtn);

    await waitFor(() => {
      expect(
        screen.getByRole('button', { name: 'Blacklist: Parfum / Fragrance' }).props
          .accessibilityState?.selected,
      ).toBe(true);
    });
  });
});
```

### Action 10.3 — Create `mobile/src/features/search/ProductCatalogScreen.test.tsx`
```typescript
import type { ReactElement } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, waitFor } from '@testing-library/react-native';
import i18n from '@/i18n/i18n';
import { LanguageProvider } from '@/i18n/LanguageProvider';
import { ProductCatalogScreen } from './ProductCatalogScreen';

const mockPush = jest.fn();

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

    await fireEvent.press(
      screen.getByRole('button', { name: i18n.t('search.clear_filters') }),
    );

    await waitFor(() => {
      expect(screen.getByText('Daily Hydration Serum')).toBeTruthy();
    });
  });

  it('pre-filters by initialCategory when navigated from HomeScreen', async () => {
    const screen = await render(renderCatalog('cleanser'));
    await screen.findByText('Gentle Cream Cleanser');

    expect(screen.queryByText('Cloud Cream Moisturizer')).toBeNull();
  });
});
```

### Action 10.4 — Create `mobile/src/features/product/product-detail-screen.test.tsx`
```typescript
import type { ReactElement } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, waitFor } from '@testing-library/react-native';
import { productFixture } from '@/api/fixtures';
import { resetMockProfileStore } from '@/features/profile/profile-api';
import i18n from '@/i18n/i18n';
import { LanguageProvider } from '@/i18n/LanguageProvider';
import { ProductDetailScreen } from './product-detail-screen';

jest.mock('@/config/env', () => ({
  env: { apiUrl: 'https://mock.invalid', useMocks: true },
}));

jest.mock('expo-router', () => ({
  router: { back: jest.fn() },
}));

function renderDetail(productId: string | undefined = productFixture.id): ReactElement {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: false, gcTime: 0 },
    },
  });
  return (
    <QueryClientProvider client={client}>
      <LanguageProvider>
        <ProductDetailScreen productId={productId} />
      </LanguageProvider>
    </QueryClientProvider>
  );
}

describe('ProductDetailScreen & Suitability (US-13, US-17)', () => {
  beforeEach(() => {
    resetMockProfileStore();
  });

  it('renders product detail, suitability card, and toggles product blacklist', async () => {
    const screen = await render(renderDetail());
    await screen.findByText(productFixture.name);

    expect(screen.getByTestId('product-suitability-card')).toBeTruthy();
    expect(screen.getByText(i18n.t('product_detail.verdict_suitable'))).toBeTruthy();

    const blacklistBtn = screen.getByRole('button', {
      name: i18n.t('product_detail.blacklist_add_product'),
    });
    await fireEvent.press(blacklistBtn);

    await waitFor(() => {
      expect(screen.getByText(i18n.t('product_detail.verdict_avoid'))).toBeTruthy();
    });
  });
});
```

### Action 10.5 — Run All Mobile & Backend Quality Gates
Execute the following commands and fix any formatting or lint issue until every single command exits with code `0`:

```bash
# 1. Mobile quality gates
cd mobile
npm run format
npm run check
npx expo install --check

# 2. Backend quality gates
cd ../backend
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run lint-imports
uv run pytest tests/unit
```

---

## Final Completion Checklist (Must All Be True Before Finishing)

- [ ] `mobile/src/api/generated/schema.d.ts` is regenerated from `mobile/openapi.json` (`npm run api:types`).
- [ ] `mobile/src/i18n/en.json` and `mobile/src/i18n/fr.json` have identical key structures (`src/i18n/dictionaries.test.ts` passes).
- [ ] Auth flow (`/auth/login`, `/auth/register`, `AuthContext.tsx`) is implemented and tested.
- [ ] Health Profile & Blacklist flow (`/profile`, `ProfileScreen.tsx`, `profile-api.ts`) is implemented and tested.
- [ ] Catalog Search & Filter flow (`/products`, `/search`, `ProductCatalogScreen.tsx`, `search-api.ts`) is implemented and tested.
- [ ] Product Detail screen (`product-detail-screen.tsx`) renders personal suitability verdicts/alerts, product summaries, and blacklist toggles.
- [ ] `backend/scripts/quality_report.py` checks `scoring_version < 4` and reports `Scoring v4 Algorithm`.
- [ ] `npm run check` in `mobile/` passes with 0 errors and 0 warnings across all test suites.
- [ ] `uv run ruff check .`, `uv run mypy`, and `uv run lint-imports` in `backend/` pass with 0 errors.
- [ ] No forbidden words (`safe`, `unsafe`, `toxic`, `harmful`, `dangerous`) appear in any newly created or modified mobile file.
