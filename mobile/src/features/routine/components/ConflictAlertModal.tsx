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
