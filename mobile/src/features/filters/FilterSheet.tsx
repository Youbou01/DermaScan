import { useState, type ReactElement } from 'react';
import {
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
  type StyleProp,
  type TextStyle,
  type ViewStyle,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import type { CategoryNode, RiskLevel } from '@/api/types';
import { getLocalizedCategory } from '@/i18n/category';
import { useTranslation } from '@/i18n/useTranslation';
import { radii, spacing, typography, useThemeColors } from '@/theme/tokens';
import {
  addIngredient,
  clearAll,
  isScoreRangeValid,
  removeIngredient,
  toggleBand,
  type FilterState,
} from './filter-state';
import { IngredientChips } from './IngredientChips';

const BANDS: readonly RiskLevel[] = ['low', 'moderate', 'high', 'unknown'];

export interface FilterSheetProps {
  visible: boolean;
  filters: FilterState;
  categories: CategoryNode[];
  onApply: (filters: FilterState) => void;
  onClose: () => void;
}

function flatten(nodes: CategoryNode[]): CategoryNode[] {
  return nodes.flatMap((node) => [node, ...flatten(node.children ?? [])]);
}

function parseScore(text: string): number | undefined {
  const digits = text.replace(/[^0-9]/g, '').slice(0, 3);
  if (digits === '') return undefined;
  return Math.min(100, Number(digits));
}

export function FilterSheet(props: FilterSheetProps): ReactElement {
  return <FilterSheetModal key={props.visible ? 'open' : 'closed'} {...props} />;
}

function FilterSheetModal({
  visible,
  filters,
  categories,
  onApply,
  onClose,
}: FilterSheetProps): ReactElement {
  const colors = useThemeColors();
  const { t } = useTranslation();
  const [draft, setDraft] = useState<FilterState>(filters);
  const valid = isScoreRangeValid(draft);

  const choice = (selected: boolean): StyleProp<ViewStyle> => [
    styles.choice,
    {
      borderColor: selected ? colors.primary : colors.border,
      backgroundColor: selected ? colors.primary : colors.surface,
    },
  ];
  const choiceText = (selected: boolean): StyleProp<TextStyle> => [
    styles.choiceText,
    { color: selected ? colors.onPrimary : colors.text },
  ];

  return (
    <Modal animationType="slide" onRequestClose={onClose} transparent visible={visible}>
      <View style={styles.backdrop}>
        <Pressable
          accessibilityLabel={t('common.close')}
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
              {t('filters.title')}
            </Text>
            <Pressable
              accessibilityLabel={t('common.close')}
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
          <ScrollView contentContainerStyle={styles.body} keyboardShouldPersistTaps="handled">
            <Text style={[styles.label, { color: colors.text }]}>{t('filters.category')}</Text>
            <View style={styles.choiceRow}>
              <Pressable
                accessibilityRole="button"
                accessibilityState={{ selected: draft.category === undefined }}
                onPress={() => setDraft({ ...draft, category: undefined })}
                style={choice(draft.category === undefined)}
              >
                <Text style={choiceText(draft.category === undefined)}>
                  {draft.category === undefined ? '✓ ' : ''}
                  {t('filters.category_all')}
                </Text>
              </Pressable>
              {flatten(categories).map((category) => {
                const selected = draft.category === category.slug;
                return (
                  <Pressable
                    accessibilityRole="button"
                    accessibilityState={{ selected }}
                    key={category.slug}
                    onPress={() => setDraft({ ...draft, category: category.slug })}
                    style={choice(selected)}
                  >
                    <Text style={choiceText(selected)}>
                      {selected ? '✓ ' : ''}
                      {getLocalizedCategory(category)}
                    </Text>
                  </Pressable>
                );
              })}
            </View>

            <Text style={[styles.label, { color: colors.text }]}>{t('filters.band')}</Text>
            <View style={styles.choiceRow}>
              {BANDS.map((band) => {
                const selected = draft.bands.includes(band);
                return (
                  <Pressable
                    accessibilityRole="button"
                    accessibilityState={{ selected }}
                    key={band}
                    onPress={() => setDraft(toggleBand(draft, band))}
                    style={choice(selected)}
                  >
                    <Text style={choiceText(selected)}>
                      {selected ? '✓ ' : ''}
                      {t(`risk.${band}`)}
                    </Text>
                  </Pressable>
                );
              })}
            </View>

            <Text style={[styles.label, { color: colors.text }]}>{t('filters.score_range')}</Text>
            <View style={styles.scoreRow}>
              <TextInput
                accessibilityLabel={t('filters.min_score')}
                keyboardType="number-pad"
                onChangeText={(text) => setDraft({ ...draft, minScore: parseScore(text) })}
                placeholder={t('filters.min_score')}
                placeholderTextColor={colors.textMuted}
                style={[
                  styles.input,
                  {
                    color: colors.text,
                    borderColor: colors.border,
                    backgroundColor: colors.surface,
                  },
                ]}
                value={draft.minScore === undefined ? '' : String(draft.minScore)}
              />
              <TextInput
                accessibilityLabel={t('filters.max_score')}
                keyboardType="number-pad"
                onChangeText={(text) => setDraft({ ...draft, maxScore: parseScore(text) })}
                placeholder={t('filters.max_score')}
                placeholderTextColor={colors.textMuted}
                style={[
                  styles.input,
                  {
                    color: colors.text,
                    borderColor: colors.border,
                    backgroundColor: colors.surface,
                  },
                ]}
                value={draft.maxScore === undefined ? '' : String(draft.maxScore)}
              />
            </View>
            {valid ? null : (
              <Text accessibilityRole="alert" style={[styles.error, { color: colors.text }]}>
                {t('filters.score_range_invalid')}
              </Text>
            )}
            <IngredientChips
              names={draft.include}
              onAdd={(name) => setDraft(addIngredient(draft, 'include', name))}
              onRemove={(name) => setDraft(removeIngredient(draft, 'include', name))}
              title={t('filters.include_title')}
            />
            <IngredientChips
              names={draft.exclude}
              onAdd={(name) => setDraft(addIngredient(draft, 'exclude', name))}
              onRemove={(name) => setDraft(removeIngredient(draft, 'exclude', name))}
              title={t('filters.exclude_title')}
            />
          </ScrollView>
          <View style={styles.footer}>
            <Pressable
              accessibilityRole="button"
              onPress={() => onApply(clearAll())}
              style={({ pressed }) => [
                styles.footerButton,
                { borderColor: colors.border, opacity: pressed ? 0.7 : 1 },
              ]}
            >
              <Text style={[styles.footerText, { color: colors.text }]}>
                {t('common.clear_all')}
              </Text>
            </Pressable>
            <Pressable
              accessibilityRole="button"
              accessibilityState={{ disabled: !valid }}
              disabled={!valid}
              onPress={() => {
                if (valid) onApply(draft);
              }}
              style={({ pressed }) => [
                styles.footerButton,
                {
                  borderColor: colors.primary,
                  backgroundColor: colors.primary,
                  opacity: !valid ? 0.4 : pressed ? 0.8 : 1,
                },
              ]}
            >
              <Text style={[styles.footerText, { color: colors.onPrimary }]}>
                {t('filters.apply')}
              </Text>
            </Pressable>
          </View>
        </SafeAreaView>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: { flex: 1, justifyContent: 'flex-end', backgroundColor: 'rgba(0, 0, 0, 0.45)' },
  sheet: {
    maxHeight: '88%',
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
  label: {
    fontSize: typography.size.md,
    lineHeight: typography.lineHeight.md,
    fontWeight: typography.weight.semibold,
  },
  choiceRow: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.md },
  choice: {
    minHeight: 44,
    justifyContent: 'center',
    paddingHorizontal: spacing.lg,
    borderWidth: 1,
    borderRadius: radii.pill,
  },
  choiceText: { fontSize: typography.size.md, lineHeight: typography.lineHeight.md },
  scoreRow: { flexDirection: 'row', gap: spacing.md },
  input: {
    flex: 1,
    minHeight: 44,
    paddingHorizontal: spacing.lg,
    borderWidth: 1,
    borderRadius: radii.lg,
    fontSize: typography.size.md,
  },
  error: { fontSize: typography.size.sm, lineHeight: typography.lineHeight.sm },
  footer: { flexDirection: 'row', gap: spacing.md, paddingBottom: spacing.lg },
  footerButton: {
    flex: 1,
    minHeight: 44,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderRadius: radii.pill,
  },
  footerText: {
    fontSize: typography.size.md,
    lineHeight: typography.lineHeight.md,
    fontWeight: typography.weight.semibold,
  },
});
