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
