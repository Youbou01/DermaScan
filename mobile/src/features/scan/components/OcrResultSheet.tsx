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
