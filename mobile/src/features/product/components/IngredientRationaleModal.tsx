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
