import { CameraView, useCameraPermissions } from 'expo-camera';
import { useRouter, type Href } from 'expo-router';
import { useRef, useState, type ReactElement } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text, TextInput, View } from 'react-native';
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
