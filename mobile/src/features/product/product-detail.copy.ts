/** Temporary English copy until MOB-03 adds the shared translation resources. */
export const productDetailCopy = {
  screenTitle: 'Product details',
  backLabel: '‹ Back',
  backAccessibilityLabel: 'Go back',
  riskIndicatorHeading: 'Risk indicator',
  brandUnavailable: 'Brand not provided',
  categoryUnavailable: 'Category unavailable',
  imageUnavailable: 'Product image unavailable',
  scoreCoverageLabel: 'Scoring coverage',
  scoreCoverageUnavailable: 'Scoring coverage is unavailable.',
  scoreCoverageDescription: 'of listed ingredients have a risk rating in the methodology.',
  ingredientsHeading: 'Ingredients',
  ingredientsEmptyTitle: 'Ingredient list unavailable',
  ingredientsEmptyDescription: 'No ingredient information is available for this product yet.',
  openRationaleHint: 'Opens the ingredient concern level and rationale.',
  rationaleHeading: 'Ingredient rationale',
  rationaleUnavailable: 'No rationale is available for this ingredient yet.',
  unmatchedExplanation:
    'This ingredient could not be matched to the rating reference. Its concern level is shown as insufficient data.',
  closeRationale: 'Close ingredient rationale',
  disclaimer:
    'Risk indicators are informational and reflect the available ingredient data and methodology. They are not medical advice.',
  missingIdTitle: 'Product unavailable',
  missingIdDescription: 'This product link does not include a product identifier.',
  notFoundTitle: 'Product not found',
  notFoundDescription: 'We could not find this product in the catalog.',
  genericErrorTitle: 'Product details unavailable',
  genericErrorDescription: 'We could not load these product details. Please try again.',
  retryLabel: 'Try again',
} as const;

export function formatScoreCoverage(coverage: number | null): string {
  if (coverage === null) {
    return productDetailCopy.scoreCoverageUnavailable;
  }

  const percentage = Math.round(coverage * 100);
  return `${productDetailCopy.scoreCoverageLabel}: ${percentage}% ${productDetailCopy.scoreCoverageDescription}`;
}
