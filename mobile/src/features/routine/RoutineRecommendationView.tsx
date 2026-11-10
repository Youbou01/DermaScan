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

const SKIN_TYPES: readonly SkinTypeOption[] = ['normal', 'dry', 'oily', 'combination', 'sensitive'];

export function RoutineRecommendationView(): ReactElement {
  const router = useRouter();
  const colors = useThemeColors();
  const { t } = useTranslation();
  const [skinType, setSkinType] = useState<SkinTypeOption>('normal');
  const [appliedMessage, setAppliedMessage] = useState(false);

  const recommendationsQuery = useRoutineRecommendationsQuery(skinType);
  const updateRoutine = useUpdateRoutineMutation();

  const handleApplyRoutine = async (slot: RoutineSlot, steps: RoutineStepItem[]): Promise<void> => {
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
              <Text style={[styles.pillText, { color: selected ? colors.onPrimary : colors.text }]}>
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
                  <Text style={[styles.stepName, { color: colors.text }]}>{step.product.name}</Text>
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
                  <Text style={[styles.stepName, { color: colors.text }]}>{step.product.name}</Text>
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
