import { useRouter, type Href } from 'expo-router';
import { useState, type ReactElement } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { EmptyState, ErrorState, ScoreBadge, Screen, Skeleton } from '@/components';
import { useTranslation } from '@/i18n/useTranslation';
import { radii, spacing, typography, useThemeColors } from '@/theme/tokens';
import { ConflictAlertModal } from './components/ConflictAlertModal';
import { ConflictWarningBanner } from './components/ConflictWarningBanner';
import {
  checkCandidateConflict,
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
  const isMutating = updateRoutine.isPending || toggleCompletion.isPending;

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
                style={[styles.tabButtonText, { color: selected ? colors.onPrimary : colors.text }]}
              >
                {label}
              </Text>
            </Pressable>
          );
        })}
      </View>

      <View
        style={[styles.habitCard, { backgroundColor: colors.surface, borderColor: colors.border }]}
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
          disabled={isMutating}
          onPress={() => {
            void toggleCompletion.mutateAsync(activeSlot);
          }}
          style={({ pressed }) => [
            styles.habitToggleButton,
            {
              backgroundColor: currentRoutine.completed_today ? colors.lowSurface : colors.primary,
              borderColor: currentRoutine.completed_today ? colors.low : colors.primary,
              opacity: pressed || isMutating ? 0.6 : 1,
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
        <EmptyState title={t('routine.empty_title')} description={t('routine.empty_description')} />
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
                  disabled={isMutating || index === 0}
                  onPress={() => handleMoveStep(index, -1)}
                  style={[
                    styles.smallButton,
                    { borderColor: colors.border, opacity: isMutating || index === 0 ? 0.4 : 1 },
                  ]}
                >
                  <Text style={{ color: colors.text }}>↑</Text>
                </Pressable>
                <Pressable
                  accessibilityRole="button"
                  accessibilityLabel={t('routine.move_down_label', { name: step.product.name })}
                  disabled={isMutating || index === steps.length - 1}
                  onPress={() => handleMoveStep(index, 1)}
                  style={[
                    styles.smallButton,
                    {
                      borderColor: colors.border,
                      opacity: isMutating || index === steps.length - 1 ? 0.4 : 1,
                    },
                  ]}
                >
                  <Text style={{ color: colors.text }}>↓</Text>
                </Pressable>
                <Pressable
                  accessibilityRole="button"
                  accessibilityLabel={t('routine.remove_step_label', { name: step.product.name })}
                  disabled={isMutating}
                  onPress={() => handleRemoveStep(index)}
                  style={[
                    styles.removeButton,
                    { borderColor: colors.high, opacity: isMutating ? 0.4 : 1 },
                  ]}
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
        {ROUTINE_CATALOG_CANDIDATES.map((candidate) => {
          const preConflict = checkCandidateConflict(candidate, steps);
          return (
            <Pressable
              key={candidate.product.id}
              accessibilityRole="button"
              accessibilityLabel={t('routine.add_step_button', { name: candidate.product.name })}
              disabled={isMutating}
              onPress={() => handleAddCandidate(candidate)}
              style={({ pressed }) => [
                styles.candidateRow,
                {
                  backgroundColor: colors.surface,
                  borderColor: colors.border,
                  opacity: pressed || isMutating ? 0.6 : 1,
                },
              ]}
            >
              <View style={styles.candidateInfo}>
                {preConflict ? (
                  <Text style={[styles.preConflictTag, { color: colors.moderate }]}>
                    ⚠ {t('conflicts.pre_check_warning')} ({preConflict.title})
                  </Text>
                ) : null}
                <Text style={[styles.productName, { color: colors.text }]}>
                  + {candidate.product.name}
                </Text>
                <Text style={[styles.activesText, { color: colors.textMuted }]}>
                  {candidate.activeIngredients.join(', ')}
                </Text>
              </View>
              <ScoreBadge score={candidate.product.score} band={candidate.product.score_band} />
            </Pressable>
          );
        })}
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
  preConflictTag: {
    fontSize: typography.size.xs,
    fontWeight: '600',
    marginBottom: 2,
  },
});
