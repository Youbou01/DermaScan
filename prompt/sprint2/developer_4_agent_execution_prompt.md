# System Role & Execution Mandate (For Coding Agent: Gemini 3.8 Flash)

You are **Developer 4 (Mobile Track B)**, an autonomous Senior React Native / Expo Engineer working inside the `mobile/` directory of the **DermaScan** repository (Expo SDK 58, React Native 0.88, Expo Router, TypeScript 6 strict, TanStack Query v5, i18next, Jest + React Native Testing Library).

Your mission is to implement Sprint 2's **Mobile Track B** features end-to-end:
- **MOB-S2-5 (`US-10`):** Instant Multilingual Packaging Ingredient OCR & Text Scanner UI (`/scan-ocr` + mode switcher on `/scan`).
- **MOB-S2-6 (`US-16`):** Daily Routine Builder (Morning AM / Evening PM steps, reorder, add/remove) & Daily Habit Completion Tracker (`/routine`).
- **MOB-S2-7 (`US-15`):** Chemical Active Conflict Warning Banner, Pre-Addition Check & Conflict Detail Modal.
- **MOB-S2-8 (`US-20`):** Recommended Morning & Night Routine Generator UI (`/routine/recommendations`) with 1-tap apply.

---

## Strict Operating Rules (Non-Negotiable)

1. **Execute Sequentially Without Improvisation:** Execute **Phase 0 (Pre-Flight Checks)** and **Micro-Steps 1 through 8** in exact order. Do not skip steps, do not invent extra dependencies, and do not touch any file outside your assigned scope.
2. **Zero Git Conflict Isolation Rules:**
   - **NEVER touch `backend/`.**
   - **NEVER edit `mobile/src/api/client.ts` or `mobile/src/api/hooks.ts`** (Developer 3 is editing those files concurrently). Keep all OCR and Routine API hooks, types, and mock state inside `mobile/src/features/scan/ocr-api.ts` and `mobile/src/features/routine/routine-api.ts`.
   - **NEVER touch `mobile/src/features/{auth,profile,search,product}/`** or `mobile/src/app/{auth,profile,products}/`.
   - In `mobile/src/i18n/en.json` and `mobile/src/i18n/fr.json`, only add the top-level keys `"ocr"`, `"routine"`, `"conflicts"`, and `"recommendations"`. Both files **MUST** have identical key structures (`src/i18n/dictionaries.test.ts` enforces this in CI).
3. **Code Quality & Linter Rules (`mobile/eslint.config.js` & `mobile/AGENTS.md`):**
   - **No `any`:** `@typescript-eslint/no-explicit-any` is an error.
   - **Explicit Return Types:** Every declared function and React component **MUST** have an explicit return type (`: ReactElement`, `: ReactElement | null`, `: void`, `: Promise<void>`).
   - **Inline Type Imports:** Enforce `@typescript-eslint/consistent-type-imports` with inline style (`import { useState, type ReactElement } from 'react';` or `import type { Foo } from './bar';`).
   - **No Floating or Misused Promises:** Never pass an `async` function directly to `onPress`. Always wrap: `onPress={() => { void handleAction(); }}`.
   - **Thin Routes Only in `src/app/`:** Files in `mobile/src/app/` must ONLY export a thin default route component rendering a screen from `mobile/src/features/`. Never put tests or helper files inside `mobile/src/app/`. Route tests go in `mobile/src/__tests__/app/`.
   - **Typed Routes Navigation:** Because `typedRoutes: true` is enabled in `app.json`, cast new route paths with `as unknown as Href` (from `expo-router`) when calling `router.push(...)`.
4. **Product & Accessibility Rules:**
   - **Forbidden Words:** Never use the words `safe`, `unsafe`, `toxic`, `harmful`, or `dangerous` in any UI text, translation string, or comment. Use `concern level`, `risk indicator`, `favorable`, `caution`, or `incompatible`.
   - **Accessibility:** Every interactive `Pressable` must have `minHeight: 44`, `accessibilityRole="button"`, and a descriptive `accessibilityLabel`. Risk and conflict indicators must always pair color + icon (`⚠`, `⬟`, `△`, `○`) + text label.

---

## Phase 0: Pre-Flight Checks (MUST Execute First)

Run these commands from the repository root before writing any code.

### Pre-Step 0.1 — Verify Node.js Version & Dependencies
```bash
cd mobile
node -v
```
- **Decision Rule:** Node.js must be `>= 22.13.0` (as required by `.nvmrc` and `.npmrc`). If `node_modules` is missing or stale, run:
  ```bash
  npm ci
  ```

### Pre-Step 0.2 — Check `.env` Configuration & Optional Backend Container State
```bash
if [ ! -f .env ]; then cp .env.example .env; fi
cat .env
```
- Check if Docker / Backend is running (optional—your code will work in both mock mode and live API mode):
  ```bash
  docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" || true
  ```
- **Decision Rule:** Ensure `mobile/.env` exists. During automated Jest tests, `jest.setup.ts` automatically provides offline defaults (`EXPO_PUBLIC_API_URL=http://localhost:8000` and `EXPO_PUBLIC_USE_MOCKS=false`). Your new API modules in Micro-Steps 2 and 4 must support `env.useMocks === true` **and** gracefully fall back to deterministic local mock state when the backend Sprint 2 endpoints (`/api/v1/analysis/*` and `/api/v1/routines/*`) return `404` or network errors during parallel development.

### Pre-Step 0.3 — Run Baseline Mobile Quality Gate
```bash
npm run check
```
- **Decision Rule:** Confirm that `tsc --noEmit`, `eslint`, `prettier --check`, and `jest` all pass on the baseline repository before proceeding to Micro-Step 1.

---

## Micro-Step 1: Add Namespaced Bilingual i18n Keys (`en.json` & `fr.json`)

### Goal
Add the `"ocr"`, `"routine"`, `"conflicts"`, and `"recommendations"` namespaces to `mobile/src/i18n/en.json` and `mobile/src/i18n/fr.json` with 100% matching key structures.

### Action 1.1 — Update `mobile/src/i18n/en.json`
Add the following four top-level keys to `mobile/src/i18n/en.json` (preserving all existing keys):

```json
  "ocr": {
    "title": "Scan ingredient label",
    "switch_to_ocr": "Scan ingredient text (OCR)",
    "switch_to_barcode": "Scan barcode instead",
    "instruction": "Capture a clear photo of the ingredient list on the packaging, or paste the text below.",
    "capture_photo": "Capture label photo",
    "analyzing": "Analyzing ingredient label…",
    "text_label": "Ingredient list text (any language)",
    "text_placeholder": "Paste or edit ingredients (e.g. Aqua, Glycerin, Niacinamide, Retinol…)",
    "analyze_button": "Analyze ingredients",
    "empty_text_error": "Please enter or capture an ingredient list to analyze.",
    "result_heading": "Instant label analysis",
    "extracted_label": "Extracted label text",
    "estimated_badge": "Estimated score",
    "reset_button": "Analyze another label"
  },
  "routine": {
    "title": "My Skincare Routine",
    "open_routine": "My Routine",
    "morning_tab": "Morning (AM)",
    "evening_tab": "Evening (PM)",
    "habit_title": "Daily habit tracker",
    "habit_completed": "Completed today",
    "habit_mark_complete": "Mark routine completed today",
    "steps_heading": "Routine steps",
    "empty_title": "No products in this routine yet",
    "empty_description": "Add products from the catalog or explore a recommended routine.",
    "add_product_heading": "Add a product to this routine",
    "add_step_button": "Add {{name}} to routine",
    "remove_step_label": "Remove {{name}} from routine",
    "move_up_label": "Move {{name}} up",
    "move_down_label": "Move {{name}} down",
    "open_recommendations": "View recommended AM/PM routines",
    "step_types": {
      "cleanser": "1. Cleanser",
      "toner": "2. Toner",
      "serum": "3. Serum / Treatment",
      "moisturizer": "4. Moisturizer",
      "sunscreen": "5. Sunscreen"
    }
  },
  "conflicts": {
    "banner_title_one": "1 ingredient conflict detected in this routine",
    "banner_title_other": "{{count}} ingredient conflicts detected in this routine",
    "banner_cta": "Review conflict details",
    "modal_heading": "Routine conflict details",
    "close_modal": "Close conflict details",
    "pre_check_warning": "Adding this product introduces a conflict with your current routine.",
    "severity_high": "High interaction concern",
    "severity_moderate": "Moderate interaction concern",
    "resolution_label": "Recommended adjustment:"
  },
  "recommendations": {
    "title": "Recommended Routines",
    "subtitle": "Conflict-free morning and evening routines tailored by skin profile.",
    "skin_type_label": "Select skin type",
    "skin_types": {
      "normal": "Normal",
      "dry": "Dry",
      "oily": "Oily",
      "combination": "Combination",
      "sensitive": "Sensitive"
    },
    "morning_heading": "Recommended Morning Routine (AM)",
    "evening_heading": "Recommended Evening Routine (PM)",
    "apply_morning": "Apply to my Morning Routine",
    "apply_evening": "Apply to my Evening Routine",
    "applied_Confirmation": "Routine updated with recommended steps.",
    "back_to_routine": "Back to my routine"
  }
```

### Action 1.2 — Update `mobile/src/i18n/fr.json`
Add the exact same four top-level keys with French translations to `mobile/src/i18n/fr.json`:

```json
  "ocr": {
    "title": "Scanner la liste d’ingrédients",
    "switch_to_ocr": "Scanner le texte des ingrédients (OCR)",
    "switch_to_barcode": "Scanner plutôt un code-barres",
    "instruction": "Prenez une photo nette de la liste d’ingrédients sur l’emballage ou collez le texte ci-dessous.",
    "capture_photo": "Photographier l’étiquette",
    "analyzing": "Analyse de l’étiquette en cours…",
    "text_label": "Texte de la liste d’ingrédients (toute langue)",
    "text_placeholder": "Collez ou modifiez les ingrédients (ex. Aqua, Glycérine, Niacinamide, Rétinol…)",
    "analyze_button": "Analyser les ingrédients",
    "empty_text_error": "Veuillez saisir ou photographier une liste d’ingrédients à analyser.",
    "result_heading": "Analyse instantanée de l’étiquette",
    "extracted_label": "Texte extrait de l’étiquette",
    "estimated_badge": "Score estimé",
    "reset_button": "Analyser une autre étiquette"
  },
  "routine": {
    "title": "Ma Routine Soin",
    "open_routine": "Ma Routine",
    "morning_tab": "Matin (AM)",
    "evening_tab": "Soir (PM)",
    "habit_title": "Suivi des habitudes quotidiennes",
    "habit_completed": "Terminée aujourd’hui",
    "habit_mark_complete": "Marquer la routine comme terminée",
    "steps_heading": "Étapes de la routine",
    "empty_title": "Aucun produit dans cette routine",
    "empty_description": "Ajoutez des produits du catalogue ou découvrez une routine recommandée.",
    "add_product_heading": "Ajouter un produit à cette routine",
    "add_step_button": "Ajouter {{name}} à la routine",
    "remove_step_label": "Retirer {{name}} de la routine",
    "move_up_label": "Monter {{name}}",
    "move_down_label": "Descendre {{name}}",
    "open_recommendations": "Voir les routines AM/PM recommandées",
    "step_types": {
      "cleanser": "1. Nettoyant",
      "toner": "2. Tonique",
      "serum": "3. Sérum / Soin ciblé",
      "moisturizer": "4. Hydratant",
      "sunscreen": "5. Écran solaire"
    }
  },
  "conflicts": {
    "banner_title_one": "1 conflit d’ingrédients détecté dans cette routine",
    "banner_title_other": "{{count}} conflits d’ingrédients détectés dans cette routine",
    "banner_cta": "Voir les détails du conflit",
    "modal_heading": "Détails des conflits de la routine",
    "close_modal": "Fermer les détails des conflits",
    "pre_check_warning": "L’ajout de ce produit crée un conflit avec votre routine actuelle.",
    "severity_high": "Préoccupation d’interaction élevée",
    "severity_moderate": "Préoccupation d’interaction modérée",
    "resolution_label": "Ajustement recommandé :"
  },
  "recommendations": {
    "title": "Routines Recommandées",
    "subtitle": "Routines matin et soir sans conflit adaptées à votre type de peau.",
    "skin_type_label": "Sélectionner le type de peau",
    "skin_types": {
      "normal": "Normale",
      "dry": "Sèche",
      "oily": "Grasse",
      "combination": "Mixte",
      "sensitive": "Sensible"
    },
    "morning_heading": "Routine Matin Recommandée (AM)",
    "evening_heading": "Routine Soir Recommandée (PM)",
    "apply_morning": "Appliquer à ma routine du matin",
    "apply_evening": "Appliquer à ma routine du soir",
    "applied_Confirmation": "Routine mise à jour avec les étapes recommandées.",
    "back_to_routine": "Retour à ma routine"
  }
```

### Verification 1
```bash
npm test -- --runInBand src/i18n/dictionaries.test.ts
```

---

## Micro-Step 2: Create Instant OCR API Module & Deterministic Analyzer (`src/features/scan/ocr-api.ts`)

### Goal
Create a self-contained API and deterministic mock/fallback module for `US-10` so `OcrScanScreen` can analyze both captured label photos and pasted multilingual ingredient lists in English, French, Arabic, or INCI nomenclature.

### Action 2.1 — Create `mobile/src/features/scan/ocr-api.ts`
Write the following exact implementation:

```typescript
import { useMutation, type UseMutationResult } from '@tanstack/react-query';
import { env } from '@/config/env';
import { getActiveApiLocale } from '@/api/locale';
import type { ProductIngredient, RiskLevel } from '@/api/types';

export interface InstantAnalysisResult {
  readonly extracted_text: string;
  readonly score: number;
  readonly score_band: RiskLevel;
  readonly score_coverage: number;
  readonly score_is_estimated: boolean;
  readonly summary: string;
  readonly ingredients: ProductIngredient[];
}

interface KnownInciEntry {
  readonly inci: string;
  readonly aliases: readonly string[];
  readonly risk: RiskLevel;
  readonly rating: number;
  readonly rationaleEn: string;
  readonly rationaleFr: string;
}

const KNOWN_DICTIONARY: readonly KnownInciEntry[] = [
  {
    inci: 'AQUA',
    aliases: ['aqua', 'water', 'eau', 'ماء'],
    risk: 'low',
    rating: 9.5,
    rationaleEn: 'Universal solvent base with low concern.',
    rationaleFr: 'Solvant universel à faible préoccupation.',
  },
  {
    inci: 'GLYCERIN',
    aliases: ['glycerin', 'glycerine', 'glycérine', 'glycerol', 'جلسرين'],
    risk: 'low',
    rating: 9.5,
    rationaleEn: 'Humectant that supports skin barrier hydration.',
    rationaleFr: 'Humectant qui soutient l’hydratation de la barrière cutanée.',
  },
  {
    inci: 'NIACINAMIDE',
    aliases: ['niacinamide', 'vitamin b3', 'vitamine b3'],
    risk: 'low',
    rating: 9.0,
    rationaleEn: 'Barrier-supporting conditioning vitamin.',
    rationaleFr: 'Vitamine apaisante soutenant la barrière cutanée.',
  },
  {
    inci: 'PANTHENOL',
    aliases: ['panthenol', 'panthénol', 'provitamin b5'],
    risk: 'low',
    rating: 9.0,
    rationaleEn: 'Soothing humectant provitamin.',
    rationaleFr: 'Provitamine hydratante et apaisante.',
  },
  {
    inci: 'RETINOL',
    aliases: ['retinol', 'rétinol', 'vitamin a'],
    risk: 'moderate',
    rating: 5.0,
    rationaleEn: 'Restricted retinoid active; review concentration and evening usage.',
    rationaleFr: 'Actif rétinoïde réglementé ; vérifier la concentration et l’usage le soir.',
  },
  {
    inci: 'SALICYLIC ACID',
    aliases: ['salicylic acid', 'acide salicylique', 'bha'],
    risk: 'moderate',
    rating: 5.5,
    rationaleEn: 'Exfoliating beta-hydroxy acid restricted in concentration.',
    rationaleFr: 'Acide bêta-hydroxylé exfoliant à concentration réglementée.',
  },
  {
    inci: 'PHENOXYETHANOL',
    aliases: ['phenoxyethanol', 'phénoxyéthanol'],
    risk: 'moderate',
    rating: 6.0,
    rationaleEn: 'Preservative restricted up to 1.0% concentration.',
    rationaleFr: 'Conservateur limité à une concentration maximale de 1,0 %.',
  },
  {
    inci: 'PARFUM',
    aliases: ['parfum', 'fragrance', 'aroma', 'عطر'],
    risk: 'high',
    rating: 2.5,
    rationaleEn: 'Fragrance mixture associated with skin sensitivity concerns.',
    rationaleFr: 'Mélange parfumant associé à des préoccupations de sensibilité cutanée.',
  },
  {
    inci: 'PROPYLPARABEN',
    aliases: ['propylparaben', 'propyl paraben'],
    risk: 'high',
    rating: 2.0,
    rationaleEn: 'Restricted preservative flagged for heightened review.',
    rationaleFr: 'Conservateur restreint signalé pour examen approfondi.',
  },
];

export const DEFAULT_SAMPLE_OCR_TEXT =
  'Ingrédients : Aqua (Eau), Glycérine, Niacinamide, Retinol, Phenoxyethanol, Parfum';

export function buildLocalInstantAnalysis(rawText: string): InstantAnalysisResult {
  const locale = getActiveApiLocale();
  const cleaned = rawText
    .replace(/^(?:ingredients?|ingr[eé]dients?|composition|المكونات)\s*[:\-]\s*/i, '')
    .trim();

  const tokens = cleaned
    .split(/[,;•|،]+/)
    .map((item) => item.trim())
    .filter((item) => item.length >= 2);

  let matchedCount = 0;
  let weightedConcernSum = 0;
  let weightSum = 0;

  const ingredients: ProductIngredient[] = tokens.map((token, idx) => {
    const position = idx + 1;
    const normalized = token
      .toLowerCase()
      .replace(/\([^)]*\)/g, '')
      .trim();
    const matchedEntry = KNOWN_DICTIONARY.find(
      (entry) =>
        entry.aliases.includes(normalized) ||
        entry.aliases.some((alias) => token.toLowerCase().includes(alias)),
    );

    const weight = Math.max(0.05, Math.pow(0.85, position - 1));
    weightSum += weight;

    if (matchedEntry) {
      matchedCount += 1;
      const concern = 1 - matchedEntry.rating / 10;
      weightedConcernSum += weight * Math.pow(concern, 3);
      return {
        position,
        name: token,
        inci_name: matchedEntry.inci,
        matched: true,
        risk_level: matchedEntry.risk,
        rationale: locale === 'fr' ? matchedEntry.rationaleFr : matchedEntry.rationaleEn,
      };
    }

    weightedConcernSum += weight * Math.pow(0.4, 3);
    return {
      position,
      name: token,
      inci_name: null,
      matched: false,
      risk_level: 'unknown',
      rationale: null,
    };
  });

  const total = Math.max(1, ingredients.length);
  const coverage = Number((matchedCount / total).toFixed(2));
  const powerMean = weightSum > 0 ? Math.cbrt(weightedConcernSum / weightSum) : 0.4;
  const score = Math.max(0, Math.min(100, Math.round(100 * (1 - powerMean))));
  const scoreBand: RiskLevel = score >= 75 ? 'low' : score >= 50 ? 'moderate' : 'high';
  const isEstimated = coverage < 0.6 || ingredients.length < 3;

  const summary =
    locale === 'fr'
      ? `Formule analysée comprenant ${ingredients.length} ingrédients (${matchedCount} reconnus dans le référentiel INCI).`
      : `Analyzed formula with ${ingredients.length} listed ingredients (${matchedCount} matched to the INCI reference).`;

  return {
    extracted_text: rawText.trim(),
    score,
    score_band: scoreBand,
    score_coverage: coverage,
    score_is_estimated: isEstimated,
    summary,
    ingredients,
  };
}

export async function analyzePackagingText(text: string): Promise<InstantAnalysisResult> {
  if (env.useMocks) {
    return buildLocalInstantAnalysis(text);
  }
  try {
    const response = await fetch(`${env.apiUrl}/api/v1/analysis/text`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept-Language': getActiveApiLocale(),
      },
      body: JSON.stringify({ ingredients_text: text }),
    });
    if (response.ok) {
      return (await response.json()) as InstantAnalysisResult;
    }
  } catch {
    // Fallback to deterministic local analyzer when offline or endpoint is not yet deployed
  }
  return buildLocalInstantAnalysis(text);
}

export async function analyzePackagingPhoto(
  photoUri?: string,
  fallbackText: string = DEFAULT_SAMPLE_OCR_TEXT,
): Promise<InstantAnalysisResult> {
  if (env.useMocks || !photoUri) {
    return buildLocalInstantAnalysis(fallbackText);
  }
  try {
    const formData = new FormData();
    formData.append('photo', {
      uri: photoUri,
      name: 'ingredient-label.jpg',
      type: 'image/jpeg',
    } as unknown as Blob);

    const response = await fetch(`${env.apiUrl}/api/v1/analysis/ocr`, {
      method: 'POST',
      headers: {
        'Accept-Language': getActiveApiLocale(),
      },
      body: formData,
    });
    if (response.ok) {
      return (await response.json()) as InstantAnalysisResult;
    }
  } catch {
    // Fallback to deterministic local analyzer when offline or endpoint is not yet deployed
  }
  return buildLocalInstantAnalysis(fallbackText);
}

export function useAnalyzeTextMutation(): UseMutationResult<InstantAnalysisResult, Error, string> {
  return useMutation({
    mutationFn: (text: string) => analyzePackagingText(text),
  });
}

export function useAnalyzePhotoMutation(): UseMutationResult<
  InstantAnalysisResult,
  Error,
  { photoUri?: string; fallbackText?: string }
> {
  return useMutation({
    mutationFn: ({ photoUri, fallbackText }) => analyzePackagingPhoto(photoUri, fallbackText),
  });
}
```

---

## Micro-Step 3: Build Instant OCR Result Sheet & Packaging OCR Scanner Screen (`US-10` — Task `MOB-S2-5`)

### Goal
Create the OCR result view (`OcrResultSheet.tsx`), the OCR scanner screen (`OcrScanScreen.tsx`), its Expo Router route (`src/app/scan-ocr.tsx`), and add a button on `ScanScreen.tsx` to switch between Barcode scanning and Ingredient OCR scanning.

### Action 3.1 — Create `mobile/src/features/scan/components/OcrResultSheet.tsx`
```typescript
import { useState, type ReactElement } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import type { ProductIngredient, RiskLevel } from '@/api/types';
import { RiskBadge, ScoreBadge } from '@/components';
import { IngredientRationaleModal } from '@/features/product/components/IngredientRationaleModal';
import { useTranslation } from '@/i18n/useTranslation';
import { radii, spacing, typography, useThemeColors } from '@/theme/tokens';
import type { InstantAnalysisResult } from '../ocr-api';

export interface OcrResultSheetProps {
  readonly result: InstantAnalysisResult;
  readonly onReset: () => void;
}

export function OcrResultSheet({ result, onReset }: OcrResultSheetProps): ReactElement {
  const colors = useThemeColors();
  const { t } = useTranslation();
  const [selectedIngredient, setSelectedIngredient] = useState<ProductIngredient | null>(null);

  return (
    <View
      testID="ocr-result-sheet"
      style={[styles.card, { backgroundColor: colors.surface, borderColor: colors.border }]}
    >
      <Text accessibilityRole="header" style={[styles.heading, { color: colors.text }]}>
        {t('ocr.result_heading')}
      </Text>
      <View style={styles.badgeRow}>
        <ScoreBadge score={result.score} band={result.score_band} />
        <RiskBadge level={result.score_band} />
      </View>
      {result.score_is_estimated ? (
        <Text style={[styles.estimatedText, { color: colors.textMuted }]}>
          {t('ocr.estimated_badge')} ({Math.round(result.score_coverage * 100)}%)
        </Text>
      ) : null}
      <Text style={[styles.summary, { color: colors.text }]}>{result.summary}</Text>
      <View style={[styles.extractedBox, { backgroundColor: colors.surfaceMuted }]}>
        <Text style={[styles.extractedTitle, { color: colors.textMuted }]}>
          {t('ocr.extracted_label')}
        </Text>
        <Text style={[styles.extractedBody, { color: colors.text }]}>{result.extracted_text}</Text>
      </View>
      <View style={styles.ingredientList}>
        {result.ingredients.map((item) => {
          const level: RiskLevel = item.matched ? item.risk_level : 'unknown';
          return (
            <Pressable
              key={`${item.position}-${item.name}`}
              accessibilityRole="button"
              accessibilityLabel={`${item.position}. ${item.name}`}
              onPress={() => setSelectedIngredient(item)}
              style={({ pressed }) => [
                styles.ingredientRow,
                {
                  backgroundColor: colors.background,
                  borderColor: colors.border,
                  opacity: pressed ? 0.75 : 1,
                },
              ]}
            >
              <View style={styles.ingredientInfo}>
                <Text style={[styles.ingredientName, { color: colors.text }]}>
                  {item.position}. {item.name}
                </Text>
                {item.inci_name && item.inci_name !== item.name ? (
                  <Text style={[styles.inciName, { color: colors.textMuted }]}>
                    {item.inci_name}
                  </Text>
                ) : null}
              </View>
              <RiskBadge level={level} />
            </Pressable>
          );
        })}
      </View>
      <Pressable
        accessibilityRole="button"
        accessibilityLabel={t('ocr.reset_button')}
        onPress={onReset}
        style={({ pressed }) => [
          styles.resetButton,
          { borderColor: colors.primary, opacity: pressed ? 0.75 : 1 },
        ]}
      >
        <Text style={[styles.resetButtonText, { color: colors.primary }]}>
          {t('ocr.reset_button')}
        </Text>
      </Pressable>
      <IngredientRationaleModal
        ingredient={selectedIngredient}
        onClose={() => setSelectedIngredient(null)}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    gap: spacing.md,
    padding: spacing.lg,
    borderWidth: 1,
    borderRadius: radii.lg,
  },
  heading: {
    fontSize: typography.size.lg,
    lineHeight: typography.lineHeight.lg,
    fontWeight: typography.weight.bold,
  },
  badgeRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    alignItems: 'center',
    gap: spacing.sm,
  },
  estimatedText: {
    fontSize: typography.size.xs,
    lineHeight: typography.lineHeight.xs,
  },
  summary: {
    fontSize: typography.size.md,
    lineHeight: typography.lineHeight.md,
  },
  extractedBox: {
    padding: spacing.md,
    borderRadius: radii.md,
    gap: spacing.xs,
  },
  extractedTitle: {
    fontSize: typography.size.xs,
    fontWeight: typography.weight.semibold,
  },
  extractedBody: {
    fontSize: typography.size.sm,
    lineHeight: typography.lineHeight.sm,
  },
  ingredientList: {
    gap: spacing.sm,
  },
  ingredientRow: {
    minHeight: 52,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: spacing.md,
    padding: spacing.md,
    borderWidth: 1,
    borderRadius: radii.md,
  },
  ingredientInfo: {
    flex: 1,
    gap: spacing.xs,
  },
  ingredientName: {
    fontSize: typography.size.md,
    fontWeight: typography.weight.medium,
  },
  inciName: {
    fontSize: typography.size.xs,
  },
  resetButton: {
    minHeight: 44,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderRadius: radii.md,
    paddingHorizontal: spacing.lg,
  },
  resetButtonText: {
    fontSize: typography.size.sm,
    fontWeight: typography.weight.semibold,
  },
});
```

### Action 3.2 — Create `mobile/src/features/scan/OcrScanScreen.tsx`
```typescript
import { CameraView, useCameraPermissions } from 'expo-camera';
import { useRouter, type Href } from 'expo-router';
import { useRef, useState, type ReactElement } from 'react';
import {
  ActivityIndicator,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { Screen } from '@/components';
import { useTranslation } from '@/i18n/useTranslation';
import { radii, spacing, typography, useThemeColors } from '@/theme/tokens';
import { OcrResultSheet } from './components/OcrResultSheet';
import {
  DEFAULT_SAMPLE_OCR_TEXT,
  useAnalyzePhotoMutation,
  useAnalyzeTextMutation,
  type InstantAnalysisResult,
} from './ocr-api';

export function OcrScanScreen(): ReactElement {
  const router = useRouter();
  const colors = useThemeColors();
  const { t } = useTranslation();
  const [permission, requestPermission] = useCameraPermissions();
  const cameraRef = useRef<CameraView | null>(null);
  const [ingredientText, setIngredientText] = useState('');
  const [validationError, setValidationError] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<InstantAnalysisResult | null>(null);

  const textMutation = useAnalyzeTextMutation();
  const photoMutation = useAnalyzePhotoMutation();
  const isPending = textMutation.isPending || photoMutation.isPending;

  const handleAnalyzeText = async (): Promise<void> => {
    const trimmed = ingredientText.trim();
    if (!trimmed) {
      setValidationError(true);
      return;
    }
    setValidationError(false);
    const res = await textMutation.mutateAsync(trimmed);
    setAnalysisResult(res);
  };

  const handleCapturePhoto = async (): Promise<void> => {
    setValidationError(false);
    let photoUri: string | undefined;
    try {
      const pic = await cameraRef.current?.takePictureAsync?.();
      photoUri = pic?.uri;
    } catch {
      photoUri = undefined;
    }
    const fallback = ingredientText.trim() || DEFAULT_SAMPLE_OCR_TEXT;
    const res = await photoMutation.mutateAsync({ photoUri, fallbackText: fallback });
    setIngredientText(res.extracted_text);
    setAnalysisResult(res);
  };

  return (
    <Screen contentContainerStyle={styles.content}>
      <View style={styles.headerRow}>
        <Text accessibilityRole="header" style={[styles.title, { color: colors.text }]}>
          {t('ocr.title')}
        </Text>
        <Pressable
          accessibilityRole="button"
          accessibilityLabel={t('ocr.switch_to_barcode')}
          onPress={() => router.push('/scan' as unknown as Href)}
          style={({ pressed }) => [
            styles.modeButton,
            { borderColor: colors.border, opacity: pressed ? 0.75 : 1 },
          ]}
        >
          <Text style={[styles.modeButtonText, { color: colors.primary }]}>
            {t('ocr.switch_to_barcode')}
          </Text>
        </Pressable>
      </View>

      <Text style={[styles.instruction, { color: colors.textMuted }]}>{t('ocr.instruction')}</Text>

      {permission?.granted ? (
        <View style={[styles.cameraContainer, { backgroundColor: colors.surfaceMuted }]}>
          <CameraView ref={cameraRef} style={StyleSheet.absoluteFill} facing="back" />
          <View pointerEvents="none" style={styles.labelFrame} />
          <Pressable
            accessibilityRole="button"
            accessibilityLabel={t('ocr.capture_photo')}
            disabled={isPending}
            onPress={() => {
              void handleCapturePhoto();
            }}
            style={({ pressed }) => [
              styles.captureButton,
              { backgroundColor: colors.primary, opacity: pressed || isPending ? 0.8 : 1 },
            ]}
          >
            <Text style={[styles.captureButtonText, { color: colors.onPrimary }]}>
              {t('ocr.capture_photo')}
            </Text>
          </Pressable>
        </View>
      ) : (
        <View
          style={[
            styles.permissionCard,
            { backgroundColor: colors.surface, borderColor: colors.border },
          ]}
        >
          <Text style={[styles.permissionText, { color: colors.text }]}>
            {t('scan.camera_denied')}
          </Text>
          <View style={styles.permissionActions}>
            {permission?.canAskAgain ? (
              <Pressable
                accessibilityRole="button"
                accessibilityLabel={t('scan.allow_camera')}
                onPress={() => {
                  void requestPermission();
                }}
                style={[styles.secondaryButton, { borderColor: colors.primary }]}
              >
                <Text style={[styles.secondaryButtonText, { color: colors.primary }]}>
                  {t('scan.allow_camera')}
                </Text>
              </Pressable>
            ) : null}
            <Pressable
              accessibilityRole="button"
              accessibilityLabel={t('ocr.capture_photo')}
              onPress={() => {
                void handleCapturePhoto();
              }}
              style={[styles.primaryButton, { backgroundColor: colors.primary }]}
            >
              <Text style={[styles.primaryButtonText, { color: colors.onPrimary }]}>
                {t('ocr.capture_photo')}
              </Text>
            </Pressable>
          </View>
        </View>
      )}

      <Text style={[styles.label, { color: colors.text }]}>{t('ocr.text_label')}</Text>
      <TextInput
        accessibilityLabel={t('ocr.text_label')}
        multiline
        numberOfLines={4}
        onChangeText={(val) => {
          setIngredientText(val);
          setValidationError(false);
        }}
        placeholder={t('ocr.text_placeholder')}
        placeholderTextColor={colors.textMuted}
        style={[
          styles.textArea,
          {
            color: colors.text,
            backgroundColor: colors.surface,
            borderColor: colors.border,
          },
        ]}
        value={ingredientText}
      />

      <Pressable
        accessibilityRole="button"
        accessibilityLabel={t('ocr.analyze_button')}
        disabled={isPending}
        onPress={() => {
          void handleAnalyzeText();
        }}
        style={({ pressed }) => [
          styles.primaryButton,
          { backgroundColor: colors.primary, opacity: pressed || isPending ? 0.8 : 1 },
        ]}
      >
        <Text style={[styles.primaryButtonText, { color: colors.onPrimary }]}>
          {t('ocr.analyze_button')}
        </Text>
      </Pressable>

      {validationError ? (
        <Text accessibilityRole="alert" style={[styles.errorText, { color: colors.high }]}>
          {t('ocr.empty_text_error')}
        </Text>
      ) : null}

      {isPending ? (
        <View accessibilityLiveRegion="polite" style={styles.statusRow}>
          <ActivityIndicator color={colors.primary} />
          <Text style={[styles.statusText, { color: colors.textMuted }]}>{t('ocr.analyzing')}</Text>
        </View>
      ) : null}

      {analysisResult ? (
        <OcrResultSheet
          result={analysisResult}
          onReset={() => {
            setAnalysisResult(null);
            setIngredientText('');
          }}
        />
      ) : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  content: { padding: spacing.lg, gap: spacing.md, paddingBottom: spacing.xxxl },
  headerRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: spacing.sm,
  },
  title: {
    fontSize: typography.size.xl,
    lineHeight: typography.lineHeight.xl,
    fontWeight: typography.weight.bold,
  },
  modeButton: {
    minHeight: 44,
    justifyContent: 'center',
    paddingHorizontal: spacing.md,
    borderWidth: 1,
    borderRadius: radii.md,
  },
  modeButtonText: {
    fontSize: typography.size.sm,
    fontWeight: typography.weight.semibold,
  },
  instruction: {
    fontSize: typography.size.sm,
    lineHeight: typography.lineHeight.sm,
  },
  cameraContainer: {
    height: 220,
    borderRadius: radii.lg,
    overflow: 'hidden',
    alignItems: 'center',
    justifyContent: 'center',
  },
  labelFrame: {
    width: '84%',
    height: 110,
    borderWidth: 2,
    borderColor: '#FFFFFF',
    borderRadius: radii.md,
  },
  captureButton: {
    position: 'absolute',
    bottom: spacing.md,
    minHeight: 44,
    justifyContent: 'center',
    paddingHorizontal: spacing.lg,
    borderRadius: radii.pill,
  },
  captureButtonText: {
    fontSize: typography.size.sm,
    fontWeight: typography.weight.semibold,
  },
  permissionCard: {
    padding: spacing.lg,
    borderWidth: 1,
    borderRadius: radii.lg,
    gap: spacing.md,
    alignItems: 'center',
  },
  permissionText: {
    fontSize: typography.size.sm,
    lineHeight: typography.lineHeight.sm,
    textAlign: 'center',
  },
  permissionActions: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.sm,
    justifyContent: 'center',
  },
  label: {
    fontSize: typography.size.md,
    fontWeight: typography.weight.semibold,
  },
  textArea: {
    minHeight: 100,
    borderWidth: 1,
    borderRadius: radii.md,
    padding: spacing.md,
    textAlignVertical: 'top',
    fontSize: typography.size.md,
  },
  primaryButton: {
    minHeight: 48,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: spacing.lg,
    borderRadius: radii.md,
  },
  primaryButtonText: {
    fontSize: typography.size.sm,
    fontWeight: typography.weight.semibold,
  },
  secondaryButton: {
    minHeight: 44,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: spacing.md,
    borderWidth: 1,
    borderRadius: radii.md,
  },
  secondaryButtonText: {
    fontSize: typography.size.sm,
    fontWeight: typography.weight.semibold,
  },
  errorText: {
    fontSize: typography.size.sm,
  },
  statusRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
  },
  statusText: {
    fontSize: typography.size.sm,
  },
});
```

### Action 3.3 — Create Thin Route `mobile/src/app/scan-ocr.tsx`
```typescript
import type { ReactElement } from 'react';
import { OcrScanScreen } from '@/features/scan/OcrScanScreen';

export default function OcrScanRoute(): ReactElement {
  return <OcrScanScreen />;
}
```

### Action 3.4 — Add OCR Switch Button to `mobile/src/features/scan/ScanScreen.tsx`
In `mobile/src/features/scan/ScanScreen.tsx`, right below the `<Text accessibilityRole="header" ...>{t('scan.title')}</Text>` heading, add a button that navigates to `/scan-ocr`:
```tsx
      <Pressable
        accessibilityRole="button"
        accessibilityLabel={t('ocr.switch_to_ocr')}
        onPress={() => router.push('/scan-ocr' as unknown as Href)}
        style={({ pressed }) => [
          styles.actionButton,
          { backgroundColor: colors.surface, borderColor: colors.border, borderWidth: 1, opacity: pressed ? 0.8 : 1 },
        ]}
      >
        <Text style={[styles.actionButtonText, { color: colors.primary }]}>
          {t('ocr.switch_to_ocr')}
        </Text>
      </Pressable>
```

### Action 3.5 — Create Unit & Component Tests `mobile/src/features/scan/OcrScanScreen.test.tsx`
Create `mobile/src/features/scan/OcrScanScreen.test.tsx` testing:
1. Validation alert when tapping **Analyze ingredients** with empty text.
2. Pasting a French/English ingredient list (`"Aqua, Glycérine, Retinol, Parfum"`), pressing **Analyze ingredients**, and verifying `ocr-result-sheet` renders the score, summary, and ingredient rows.
3. Tapping **Capture label photo** triggers instant OCR analysis and renders the breakdown.

---

## Micro-Step 4: Create Routine, Conflict Engine & Recommendation State/API Module (`src/features/routine/routine-api.ts`)

### Goal
Create a self-contained TanStack Query + deterministic conflict engine module in `mobile/src/features/routine/routine-api.ts` for `US-15`, `US-16`, and `US-20`.

### Action 4.1 — Create `mobile/src/features/routine/routine-api.ts`
Write the following exact implementation:

```typescript
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

interface InternalRoutineStore {
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
      const updated: RoutineData = {
        ...routineStore[slot],
        steps: normalizedSteps,
        conflicts,
      };
      routineStore = {
        ...routineStore,
        [slot]: updated,
      };
      return updated;
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
      const updated: RoutineData = {
        ...current,
        completed_today: !current.completed_today,
      };
      routineStore = {
        ...routineStore,
        [slot]: updated,
      };
      return updated;
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['routines'] });
    },
  });
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
```

---

## Micro-Step 5: Build Chemical Conflict Warning Banner & Alert Modal (`US-15` — Task `MOB-S2-7`)

### Goal
Create the reusable inline conflict warning banner and accessible modal sheet that explain pairwise ingredient conflicts (`Retinoid x AHA/BHA`, `Retinoid x Benzoyl Peroxide`, `Vitamin C x Intensive Actives`) and provide actionable resolution tips.

### Action 5.1 — Create `mobile/src/features/routine/components/ConflictWarningBanner.tsx`
```typescript
import type { ReactElement } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { useTranslation } from '@/i18n/useTranslation';
import { radii, spacing, typography, useThemeColors } from '@/theme/tokens';
import type { RoutineConflict } from '../routine-api';

export interface ConflictWarningBannerProps {
  readonly conflicts: readonly RoutineConflict[];
  readonly onPressDetails: () => void;
}

export function ConflictWarningBanner({
  conflicts,
  onPressDetails,
}: ConflictWarningBannerProps): ReactElement | null {
  const colors = useThemeColors();
  const { t } = useTranslation();

  if (conflicts.length === 0) {
    return null;
  }

  const hasHigh = conflicts.some((c) => c.severity === 'high');
  const fg = hasHigh ? colors.high : colors.moderate;
  const bg = hasHigh ? colors.highSurface : colors.moderateSurface;
  const title =
    conflicts.length === 1
      ? t('conflicts.banner_title_one')
      : t('conflicts.banner_title_other', { count: conflicts.length });

  return (
    <View
      accessibilityRole="alert"
      testID="conflict-warning-banner"
      style={[styles.banner, { backgroundColor: bg, borderColor: fg }]}
    >
      <View style={styles.headerRow}>
        <Text accessibilityElementsHidden style={[styles.icon, { color: fg }]}>
          {hasHigh ? '⬟' : '△'}
        </Text>
        <Text style={[styles.title, { color: fg }]}>{title}</Text>
      </View>
      <Text style={[styles.preview, { color: colors.text }]}>
        {conflicts[0]?.title}: {conflicts[0]?.product_a_name} + {conflicts[0]?.product_b_name}
      </Text>
      <Pressable
        accessibilityRole="button"
        accessibilityLabel={t('conflicts.banner_cta')}
        onPress={onPressDetails}
        style={({ pressed }) => [
          styles.button,
          { borderColor: fg, opacity: pressed ? 0.75 : 1 },
        ]}
      >
        <Text style={[styles.buttonText, { color: fg }]}>{t('conflicts.banner_cta')}</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  banner: {
    gap: spacing.sm,
    padding: spacing.md,
    borderWidth: 1,
    borderRadius: radii.md,
  },
  headerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.xs,
  },
  icon: {
    fontSize: typography.size.lg,
    fontWeight: typography.weight.bold,
  },
  title: {
    flex: 1,
    fontSize: typography.size.md,
    lineHeight: typography.lineHeight.md,
    fontWeight: typography.weight.bold,
  },
  preview: {
    fontSize: typography.size.sm,
    lineHeight: typography.lineHeight.sm,
  },
  button: {
    minHeight: 44,
    alignSelf: 'flex-start',
    justifyContent: 'center',
    paddingHorizontal: spacing.md,
    borderWidth: 1,
    borderRadius: radii.md,
  },
  buttonText: {
    fontSize: typography.size.sm,
    fontWeight: typography.weight.semibold,
  },
});
```

### Action 5.2 — Create `mobile/src/features/routine/components/ConflictAlertModal.tsx`
```typescript
import type { ReactElement } from 'react';
import { Modal, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useTranslation } from '@/i18n/useTranslation';
import { radii, spacing, typography, useThemeColors } from '@/theme/tokens';
import type { RoutineConflict } from '../routine-api';

export interface ConflictAlertModalProps {
  readonly visible: boolean;
  readonly conflicts: readonly RoutineConflict[];
  readonly onClose: () => void;
}

export function ConflictAlertModal({
  visible,
  conflicts,
  onClose,
}: ConflictAlertModalProps): ReactElement {
  const colors = useThemeColors();
  const { t } = useTranslation();

  return (
    <Modal animationType="slide" onRequestClose={onClose} transparent visible={visible}>
      <View style={styles.backdrop}>
        <Pressable
          accessibilityLabel={t('conflicts.close_modal')}
          accessibilityRole="button"
          onPress={onClose}
          style={StyleSheet.absoluteFill}
        />
        <SafeAreaView
          accessibilityViewIsModal
          edges={['bottom']}
          style={[styles.sheet, { backgroundColor: colors.surface }]}
        >
          <View style={styles.headerRow}>
            <Text accessibilityRole="header" style={[styles.heading, { color: colors.text }]}>
              {t('conflicts.modal_heading')}
            </Text>
            <Pressable
              accessibilityLabel={t('conflicts.close_modal')}
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
            {conflicts.map((conflict) => {
              const isHigh = conflict.severity === 'high';
              const accent = isHigh ? colors.high : colors.moderate;
              return (
                <View
                  key={`${conflict.code}-${conflict.product_a_id}-${conflict.product_b_id}`}
                  style={[styles.conflictCard, { borderColor: accent }]}
                >
                  <Text style={[styles.severityTag, { color: accent }]}>
                    {isHigh ? '⬟ ' : '△ '}
                    {isHigh ? t('conflicts.severity_high') : t('conflicts.severity_moderate')}
                  </Text>
                  <Text style={[styles.conflictTitle, { color: colors.text }]}>
                    {conflict.title}
                  </Text>
                  <Text style={[styles.productsLine, { color: colors.textMuted }]}>
                    {conflict.product_a_name} ({conflict.ingredient_a}) × {conflict.product_b_name}{' '}
                    ({conflict.ingredient_b})
                  </Text>
                  <Text style={[styles.detail, { color: colors.text }]}>{conflict.detail}</Text>
                  <Text style={[styles.resolutionLabel, { color: colors.primary }]}>
                    {t('conflicts.resolution_label')}
                  </Text>
                  <Text style={[styles.detail, { color: colors.textMuted }]}>
                    {conflict.resolution}
                  </Text>
                </View>
              );
            })}
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
  headerRow: {
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
  closeText: {
    fontSize: typography.size.xl,
    lineHeight: typography.lineHeight.xl,
  },
  body: {
    gap: spacing.md,
    paddingTop: spacing.lg,
    paddingBottom: spacing.xl,
  },
  conflictCard: {
    gap: spacing.xs,
    padding: spacing.md,
    borderWidth: 1,
    borderRadius: radii.md,
  },
  severityTag: {
    fontSize: typography.size.xs,
    fontWeight: typography.weight.bold,
  },
  conflictTitle: {
    fontSize: typography.size.md,
    fontWeight: typography.weight.bold,
  },
  productsLine: {
    fontSize: typography.size.xs,
  },
  detail: {
    fontSize: typography.size.sm,
    lineHeight: typography.lineHeight.sm,
  },
  resolutionLabel: {
    marginTop: spacing.xs,
    fontSize: typography.size.xs,
    fontWeight: typography.weight.bold,
  },
});
```

---

## Micro-Step 6: Build Daily Routine Builder & Habit Tracker Screen (`US-16` — Task `MOB-S2-6`)

### Goal
Create `RoutineScreen.tsx`, mount it at `mobile/src/app/routine/index.tsx`, and add navigation entry points in `HomeScreen.tsx`.

### Action 6.1 — Create `mobile/src/features/routine/RoutineScreen.tsx`
```typescript
import { useRouter, type Href } from 'expo-router';
import { useState, type ReactElement } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { EmptyState, ErrorState, ScoreBadge, Screen, Skeleton } from '@/components';
import { useTranslation } from '@/i18n/useTranslation';
import { radii, spacing, typography, useThemeColors } from '@/theme/tokens';
import { ConflictAlertModal } from './components/ConflictAlertModal';
import { ConflictWarningBanner } from './components/ConflictWarningBanner';
import {
  ROUTINE_CATALOG_CANDIDATES,
  useRoutinesQuery,
  useToggleRoutineCompletionMutation,
  useUpdateRoutineMutation,
  type CatalogCandidateProduct,
  type RoutineSlot,
  type RoutineStepItem,
} from './routine-api';

export function RoutineScreen(): ReactElement {
  const router = useRouter();
  const colors = useThemeColors();
  const { t } = useTranslation();
  const [activeSlot, setActiveSlot] = useState<RoutineSlot>('morning');
  const [conflictModalOpen, setConflictModalOpen] = useState(false);

  const routinesQuery = useRoutinesQuery();
  const updateRoutine = useUpdateRoutineMutation();
  const toggleCompletion = useToggleRoutineCompletionMutation();

  if (routinesQuery.isPending) {
    return (
      <Screen contentContainerStyle={styles.content}>
        <Skeleton height={48} />
        <Skeleton height={90} />
        <Skeleton height={90} />
      </Screen>
    );
  }

  if (routinesQuery.isError || !routinesQuery.data) {
    return (
      <Screen>
        <ErrorState
          onRetry={() => {
            void routinesQuery.refetch();
          }}
        />
      </Screen>
    );
  }

  const currentRoutine = routinesQuery.data[activeSlot];
  const steps = currentRoutine.steps;

  const handleRemoveStep = (index: number): void => {
    const nextSteps = steps.filter((_, idx) => idx !== index);
    void updateRoutine.mutateAsync({ slot: activeSlot, steps: nextSteps });
  };

  const handleMoveStep = (index: number, direction: -1 | 1): void => {
    const targetIndex = index + direction;
    if (targetIndex < 0 || targetIndex >= steps.length) {
      return;
    }
    const copy = [...steps];
    const currentItem = copy[index]!;
    copy[index] = copy[targetIndex]!;
    copy[targetIndex] = currentItem;
    void updateRoutine.mutateAsync({ slot: activeSlot, steps: copy });
  };

  const handleAddCandidate = (candidate: CatalogCandidateProduct): void => {
    const nextStep: RoutineStepItem = {
      step_order: steps.length + 1,
      step_type: candidate.defaultStepType,
      product: candidate.product,
      active_ingredients: candidate.activeIngredients,
    };
    void updateRoutine.mutateAsync({
      slot: activeSlot,
      steps: [...steps, nextStep],
    });
  };

  return (
    <Screen contentContainerStyle={styles.content}>
      <Text accessibilityRole="header" style={[styles.title, { color: colors.text }]}>
        {t('routine.title')}
      </Text>

      <View style={styles.tabRow}>
        {(['morning', 'evening'] as const).map((slot) => {
          const selected = activeSlot === slot;
          const label = slot === 'morning' ? t('routine.morning_tab') : t('routine.evening_tab');
          return (
            <Pressable
              key={slot}
              accessibilityRole="button"
              accessibilityLabel={label}
              accessibilityState={{ selected }}
              onPress={() => setActiveSlot(slot)}
              style={[
                styles.tabButton,
                {
                  backgroundColor: selected ? colors.primary : colors.surface,
                  borderColor: selected ? colors.primary : colors.border,
                },
              ]}
            >
              <Text
                style={[
                  styles.tabButtonText,
                  { color: selected ? colors.onPrimary : colors.text },
                ]}
              >
                {label}
              </Text>
            </Pressable>
          );
        })}
      </View>

      <View
        style={[
          styles.habitCard,
          { backgroundColor: colors.surface, borderColor: colors.border },
        ]}
      >
        <View style={styles.habitTextCol}>
          <Text style={[styles.habitTitle, { color: colors.text }]}>
            {t('routine.habit_title')}
          </Text>
          <Text style={[styles.habitStatus, { color: colors.textMuted }]}>
            {currentRoutine.completed_today
              ? `✓ ${t('routine.habit_completed')}`
              : t('routine.habit_mark_complete')}
          </Text>
        </View>
        <Pressable
          accessibilityRole="button"
          accessibilityLabel={
            currentRoutine.completed_today
              ? t('routine.habit_completed')
              : t('routine.habit_mark_complete')
          }
          accessibilityState={{ checked: currentRoutine.completed_today }}
          onPress={() => {
            void toggleCompletion.mutateAsync(activeSlot);
          }}
          style={[
            styles.habitToggleButton,
            {
              backgroundColor: currentRoutine.completed_today
                ? colors.lowSurface
                : colors.primary,
              borderColor: currentRoutine.completed_today ? colors.low : colors.primary,
            },
          ]}
        >
          <Text
            style={[
              styles.habitToggleText,
              { color: currentRoutine.completed_today ? colors.low : colors.onPrimary },
            ]}
          >
            {currentRoutine.completed_today
              ? t('routine.habit_completed')
              : t('routine.habit_mark_complete')}
          </Text>
        </Pressable>
      </View>

      <ConflictWarningBanner
        conflicts={currentRoutine.conflicts}
        onPressDetails={() => setConflictModalOpen(true)}
      />

      <Pressable
        accessibilityRole="button"
        accessibilityLabel={t('routine.open_recommendations')}
        onPress={() => router.push('/routine/recommendations' as unknown as Href)}
        style={[
          styles.recommendLink,
          { backgroundColor: colors.surfaceMuted, borderColor: colors.border },
        ]}
      >
        <Text style={[styles.recommendLinkText, { color: colors.primary }]}>
          {t('routine.open_recommendations')}
        </Text>
      </Pressable>

      <Text accessibilityRole="header" style={[styles.sectionHeading, { color: colors.text }]}>
        {t('routine.steps_heading')}
      </Text>

      {steps.length === 0 ? (
        <EmptyState
          title={t('routine.empty_title')}
          description={t('routine.empty_description')}
        />
      ) : (
        <View style={styles.stepsList}>
          {steps.map((step, index) => (
            <View
              key={`${step.product.id}-${index}`}
              style={[
                styles.stepCard,
                { backgroundColor: colors.surface, borderColor: colors.border },
              ]}
            >
              <View style={styles.stepTopRow}>
                <View style={styles.stepInfo}>
                  <Text style={[styles.stepTypeLabel, { color: colors.primary }]}>
                    {t(`routine.step_types.${step.step_type}`)}
                  </Text>
                  <Text style={[styles.productName, { color: colors.text }]}>
                    {step.product.name}
                  </Text>
                  <Text style={[styles.activesText, { color: colors.textMuted }]}>
                    {step.active_ingredients.join(', ')}
                  </Text>
                </View>
                <ScoreBadge score={step.product.score} band={step.product.score_band} />
              </View>
              <View style={styles.stepActionsRow}>
                <Pressable
                  accessibilityRole="button"
                  accessibilityLabel={t('routine.move_up_label', { name: step.product.name })}
                  disabled={index === 0}
                  onPress={() => handleMoveStep(index, -1)}
                  style={[
                    styles.smallButton,
                    { borderColor: colors.border, opacity: index === 0 ? 0.4 : 1 },
                  ]}
                >
                  <Text style={{ color: colors.text }}>↑</Text>
                </Pressable>
                <Pressable
                  accessibilityRole="button"
                  accessibilityLabel={t('routine.move_down_label', { name: step.product.name })}
                  disabled={index === steps.length - 1}
                  onPress={() => handleMoveStep(index, 1)}
                  style={[
                    styles.smallButton,
                    {
                      borderColor: colors.border,
                      opacity: index === steps.length - 1 ? 0.4 : 1,
                    },
                  ]}
                >
                  <Text style={{ color: colors.text }}>↓</Text>
                </Pressable>
                <Pressable
                  accessibilityRole="button"
                  accessibilityLabel={t('routine.remove_step_label', { name: step.product.name })}
                  onPress={() => handleRemoveStep(index)}
                  style={[styles.removeButton, { borderColor: colors.high }]}
                >
                  <Text style={[styles.removeButtonText, { color: colors.high }]}>×</Text>
                </Pressable>
              </View>
            </View>
          ))}
        </View>
      )}

      <Text accessibilityRole="header" style={[styles.sectionHeading, { color: colors.text }]}>
        {t('routine.add_product_heading')}
      </Text>
      <View style={styles.candidatesList}>
        {ROUTINE_CATALOG_CANDIDATES.map((candidate) => (
          <Pressable
            key={candidate.product.id}
            accessibilityRole="button"
            accessibilityLabel={t('routine.add_step_button', { name: candidate.product.name })}
            onPress={() => handleAddCandidate(candidate)}
            style={({ pressed }) => [
              styles.candidateRow,
              {
                backgroundColor: colors.surface,
                borderColor: colors.border,
                opacity: pressed ? 0.75 : 1,
              },
            ]}
          >
            <View style={styles.candidateInfo}>
              <Text style={[styles.productName, { color: colors.text }]}>
                + {candidate.product.name}
              </Text>
              <Text style={[styles.activesText, { color: colors.textMuted }]}>
                {candidate.activeIngredients.join(', ')}
              </Text>
            </View>
            <ScoreBadge score={candidate.product.score} band={candidate.product.score_band} />
          </Pressable>
        ))}
      </View>

      <ConflictAlertModal
        visible={conflictModalOpen}
        conflicts={currentRoutine.conflicts}
        onClose={() => setConflictModalOpen(false)}
      />
    </Screen>
  );
}

const styles = StyleSheet.create({
  content: { padding: spacing.lg, gap: spacing.md, paddingBottom: spacing.xxxl },
  title: {
    fontSize: typography.size.xl,
    lineHeight: typography.lineHeight.xl,
    fontWeight: typography.weight.bold,
  },
  tabRow: {
    flexDirection: 'row',
    gap: spacing.sm,
  },
  tabButton: {
    flex: 1,
    minHeight: 44,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderRadius: radii.md,
    paddingHorizontal: spacing.md,
  },
  tabButtonText: {
    fontSize: typography.size.sm,
    fontWeight: typography.weight.semibold,
  },
  habitCard: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: spacing.sm,
    padding: spacing.md,
    borderWidth: 1,
    borderRadius: radii.md,
  },
  habitTextCol: {
    flex: 1,
    minWidth: 160,
    gap: spacing.xs,
  },
  habitTitle: {
    fontSize: typography.size.md,
    fontWeight: typography.weight.semibold,
  },
  habitStatus: {
    fontSize: typography.size.xs,
  },
  habitToggleButton: {
    minHeight: 44,
    justifyContent: 'center',
    paddingHorizontal: spacing.md,
    borderWidth: 1,
    borderRadius: radii.md,
  },
  habitToggleText: {
    fontSize: typography.size.xs,
    fontWeight: typography.weight.semibold,
  },
  recommendLink: {
    minHeight: 44,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: spacing.md,
    borderWidth: 1,
    borderRadius: radii.md,
  },
  recommendLinkText: {
    fontSize: typography.size.sm,
    fontWeight: typography.weight.semibold,
  },
  sectionHeading: {
    marginTop: spacing.sm,
    fontSize: typography.size.lg,
    lineHeight: typography.lineHeight.lg,
    fontWeight: typography.weight.bold,
  },
  stepsList: {
    gap: spacing.sm,
  },
  stepCard: {
    gap: spacing.sm,
    padding: spacing.md,
    borderWidth: 1,
    borderRadius: radii.md,
  },
  stepTopRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: spacing.sm,
  },
  stepInfo: {
    flex: 1,
    gap: 2,
  },
  stepTypeLabel: {
    fontSize: typography.size.xs,
    fontWeight: typography.weight.bold,
  },
  productName: {
    fontSize: typography.size.md,
    fontWeight: typography.weight.semibold,
  },
  activesText: {
    fontSize: typography.size.xs,
  },
  stepActionsRow: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
    gap: spacing.xs,
  },
  smallButton: {
    minWidth: 44,
    minHeight: 44,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderRadius: radii.sm,
  },
  removeButton: {
    minWidth: 44,
    minHeight: 44,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderRadius: radii.sm,
  },
  removeButtonText: {
    fontSize: typography.size.lg,
    fontWeight: typography.weight.bold,
  },
  candidatesList: {
    gap: spacing.sm,
  },
  candidateRow: {
    minHeight: 56,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: spacing.sm,
    padding: spacing.md,
    borderWidth: 1,
    borderRadius: radii.md,
  },
  candidateInfo: {
    flex: 1,
    gap: 2,
  },
});
```

### Action 6.2 — Create Thin Route `mobile/src/app/routine/index.tsx`
```typescript
import type { ReactElement } from 'react';
import { RoutineScreen } from '@/features/routine/RoutineScreen';

export default function RoutineRoute(): ReactElement {
  return <RoutineScreen />;
}
```

### Action 6.3 — Add Routine Entry Button in `mobile/src/features/home/HomeScreen.tsx`
In `HomeHero` inside `mobile/src/features/home/HomeScreen.tsx`, wrap the existing scan `Pressable` in a flex row (`flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm, marginTop: spacing.lg`) and add a second `Pressable` next to it that navigates to `/routine` with label `{t('routine.open_routine')}`. Ensure all existing `home-route.test.tsx` assertions remain green.

---

## Micro-Step 7: Build Recommended Morning & Night Routine Generator Screen (`US-20` — Task `MOB-S2-8`)

### Goal
Create `RoutineRecommendationView.tsx` and mount it at `mobile/src/app/routine/recommendations.tsx` so users can select a skin type (`normal`, `dry`, `oily`, `combination`, `sensitive`), inspect conflict-free AM and PM routines, and apply either routine in 1 tap.

### Action 7.1 — Create `mobile/src/features/routine/RoutineRecommendationView.tsx`
```typescript
import { useRouter, type Href } from 'expo-router';
import { useState, type ReactElement } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { ScoreBadge, Screen } from '@/components';
import { useTranslation } from '@/i18n/useTranslation';
import { radii, spacing, typography, useThemeColors } from '@/theme/tokens';
import {
  useRoutineRecommendationsQuery,
  useUpdateRoutineMutation,
  type RoutineSlot,
  type RoutineStepItem,
  type SkinTypeOption,
} from './routine-api';

const SKIN_TYPES: readonly SkinTypeOption[] = [
  'normal',
  'dry',
  'oily',
  'combination',
  'sensitive',
];

export function RoutineRecommendationView(): ReactElement {
  const router = useRouter();
  const colors = useThemeColors();
  const { t } = useTranslation();
  const [skinType, setSkinType] = useState<SkinTypeOption>('normal');
  const [appliedMessage, setAppliedMessage] = useState(false);

  const recommendationsQuery = useRoutineRecommendationsQuery(skinType);
  const updateRoutine = useUpdateRoutineMutation();

  const handleApplyRoutine = async (
    slot: RoutineSlot,
    steps: RoutineStepItem[],
  ): Promise<void> => {
    await updateRoutine.mutateAsync({ slot, steps });
    setAppliedMessage(true);
  };

  const data = recommendationsQuery.data;

  return (
    <Screen contentContainerStyle={styles.content}>
      <Pressable
        accessibilityRole="button"
        accessibilityLabel={t('recommendations.back_to_routine')}
        onPress={() => router.push('/routine' as unknown as Href)}
        style={[styles.backButton, { borderColor: colors.border }]}
      >
        <Text style={[styles.backButtonText, { color: colors.primary }]}>
          ‹ {t('recommendations.back_to_routine')}
        </Text>
      </Pressable>

      <Text accessibilityRole="header" style={[styles.title, { color: colors.text }]}>
        {t('recommendations.title')}
      </Text>
      <Text style={[styles.subtitle, { color: colors.textMuted }]}>
        {t('recommendations.subtitle')}
      </Text>

      <Text style={[styles.sectionLabel, { color: colors.text }]}>
        {t('recommendations.skin_type_label')}
      </Text>
      <View style={styles.pillsRow}>
        {SKIN_TYPES.map((option) => {
          const selected = option === skinType;
          const label = t(`recommendations.skin_types.${option}`);
          return (
            <Pressable
              key={option}
              accessibilityRole="button"
              accessibilityLabel={label}
              accessibilityState={{ selected }}
              onPress={() => {
                setSkinType(option);
                setAppliedMessage(false);
              }}
              style={[
                styles.pill,
                {
                  backgroundColor: selected ? colors.primary : colors.surface,
                  borderColor: selected ? colors.primary : colors.border,
                },
              ]}
            >
              <Text
                style={[
                  styles.pillText,
                  { color: selected ? colors.onPrimary : colors.text },
                ]}
              >
                {label}
              </Text>
            </Pressable>
          );
        })}
      </View>

      {appliedMessage ? (
        <Text accessibilityRole="status" style={[styles.statusBanner, { color: colors.primary }]}>
          {t('recommendations.applied_Confirmation')}
        </Text>
      ) : null}

      {data ? (
        <>
          <View
            style={[
              styles.routineBlock,
              { backgroundColor: colors.surface, borderColor: colors.border },
            ]}
          >
            <Text accessibilityRole="header" style={[styles.blockTitle, { color: colors.text }]}>
              {t('recommendations.morning_heading')}
            </Text>
            {data.morning.map((step) => (
              <View key={`am-${step.step_order}`} style={styles.stepRow}>
                <View style={styles.stepInfo}>
                  <Text style={[styles.stepType, { color: colors.primary }]}>
                    {t(`routine.step_types.${step.step_type}`)}
                  </Text>
                  <Text style={[styles.stepName, { color: colors.text }]}>
                    {step.product.name}
                  </Text>
                </View>
                <ScoreBadge score={step.product.score} band={step.product.score_band} />
              </View>
            ))}
            <Pressable
              accessibilityRole="button"
              accessibilityLabel={t('recommendations.apply_morning')}
              onPress={() => {
                void handleApplyRoutine('morning', data.morning);
              }}
              style={[styles.applyButton, { backgroundColor: colors.primary }]}
            >
              <Text style={[styles.applyButtonText, { color: colors.onPrimary }]}>
                {t('recommendations.apply_morning')}
              </Text>
            </Pressable>
          </View>

          <View
            style={[
              styles.routineBlock,
              { backgroundColor: colors.surface, borderColor: colors.border },
            ]}
          >
            <Text accessibilityRole="header" style={[styles.blockTitle, { color: colors.text }]}>
              {t('recommendations.evening_heading')}
            </Text>
            {data.evening.map((step) => (
              <View key={`pm-${step.step_order}`} style={styles.stepRow}>
                <View style={styles.stepInfo}>
                  <Text style={[styles.stepType, { color: colors.primary }]}>
                    {t(`routine.step_types.${step.step_type}`)}
                  </Text>
                  <Text style={[styles.stepName, { color: colors.text }]}>
                    {step.product.name}
                  </Text>
                </View>
                <ScoreBadge score={step.product.score} band={step.product.score_band} />
              </View>
            ))}
            <Pressable
              accessibilityRole="button"
              accessibilityLabel={t('recommendations.apply_evening')}
              onPress={() => {
                void handleApplyRoutine('evening', data.evening);
              }}
              style={[styles.applyButton, { backgroundColor: colors.primary }]}
            >
              <Text style={[styles.applyButtonText, { color: colors.onPrimary }]}>
                {t('recommendations.apply_evening')}
              </Text>
            </Pressable>
          </View>
        </>
      ) : null}
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
  backButtonText: {
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
  sectionLabel: {
    fontSize: typography.size.md,
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
    fontSize: typography.size.sm,
    fontWeight: typography.weight.semibold,
  },
  statusBanner: {
    fontSize: typography.size.sm,
    fontWeight: typography.weight.semibold,
  },
  routineBlock: {
    gap: spacing.md,
    padding: spacing.lg,
    borderWidth: 1,
    borderRadius: radii.lg,
  },
  blockTitle: {
    fontSize: typography.size.lg,
    fontWeight: typography.weight.bold,
  },
  stepRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: spacing.sm,
  },
  stepInfo: {
    flex: 1,
    gap: 2,
  },
  stepType: {
    fontSize: typography.size.xs,
    fontWeight: typography.weight.bold,
  },
  stepName: {
    fontSize: typography.size.md,
    fontWeight: typography.weight.medium,
  },
  applyButton: {
    minHeight: 48,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: radii.md,
    paddingHorizontal: spacing.lg,
  },
  applyButtonText: {
    fontSize: typography.size.sm,
    fontWeight: typography.weight.semibold,
  },
});
```

### Action 7.2 — Create Thin Route `mobile/src/app/routine/recommendations.tsx`
```typescript
import type { ReactElement } from 'react';
import { RoutineRecommendationView } from '@/features/routine/RoutineRecommendationView';

export default function RoutineRecommendationsRoute(): ReactElement {
  return <RoutineRecommendationView />;
}
```

---

## Micro-Step 8: Write Comprehensive Tests & Run the Full Quality Gate

### Action 8.1 — Create `mobile/src/features/routine/RoutineScreen.test.tsx`
Write Jest + React Native Testing Library tests verifying:
1. **Routine Builder & Habit Tracker (`US-16`):**
   - Renders Morning (AM) steps by default and switches to Evening (PM).
   - Toggles daily habit completion button and updates state to `Completed today`.
   - Removes a step from the routine.
2. **Chemical Conflict Detection & Modal (`US-15`):**
   - Adding both `Night Renewal Retinol 0.3% Serum` and `Glycolic Acid 7% Resurfacing Toner` to the same routine triggers `conflict-warning-banner` (`1 ingredient conflict detected in this routine`).
   - Pressing **Review conflict details** opens the conflict modal displaying `Retinoid + Exfoliating Acid (AHA/BHA) Conflict` and its resolution advice.
3. **Recommended Routines (`US-20`):**
   - Renders `RoutineRecommendationView`, switches skin type to `Sensitive`, and applies the recommended Morning routine.

### Action 8.2 — Format, Typecheck, Lint, and Run All Jest Suites
Execute the following commands from `mobile/` and fix any formatting or lint issue until every single check exits with code `0`:

```bash
cd mobile
npm run format
npm run check
npx expo install --check
npx expo-doctor
```

### Final Verification Checklist (Must All Be True Before Finishing)
- [ ] `npm run check` passes (`tsc --noEmit`, `eslint . --max-warnings=0`, `prettier --check .`, and `jest --ci` all green).
- [ ] `src/i18n/dictionaries.test.ts` passes (identical key structures in `en.json` and `fr.json`).
- [ ] Zero files outside `mobile/` were modified, and `mobile/src/api/client.ts` / `mobile/src/api/hooks.ts` were not modified.
- [ ] No forbidden words (`safe`, `unsafe`, `toxic`, `harmful`, `dangerous`) appear in any newly created file.
