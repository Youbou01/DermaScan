import { CameraView, useCameraPermissions, type BarcodeScanningResult } from 'expo-camera';
import { useIsFocused, useRouter, type Href } from 'expo-router';
import { useCallback, useEffect, useRef, useState, type ReactElement } from 'react';
import {
  ActivityIndicator,
  Linking,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { ApiError } from '@/api/errors';
import { useProductByBarcodeQuery } from '@/api/hooks';
import { ErrorState, Screen, Skeleton } from '@/components';
import { useTranslation } from '@/i18n/useTranslation';
import { radii, spacing, typography, useThemeColors } from '@/theme/tokens';

const BARCODE_TYPES = ['ean13', 'ean8', 'upc_a'] as const;
const SCAN_DEBOUNCE_MS = 1800;
const PRODUCT_NOT_FOUND = 'urn:skincare:problem:product-not-found';
const INVALID_BARCODE = 'urn:skincare:problem:invalid-barcode';

export function ScanScreen(): ReactElement {
  const router = useRouter();
  const isFocused = useIsFocused();
  const colors = useThemeColors();
  const { t } = useTranslation();
  const [permission, requestPermission] = useCameraPermissions();
  const [torchEnabled, setTorchEnabled] = useState(false);
  const [barcode, setBarcode] = useState<string | undefined>();
  const [manualBarcode, setManualBarcode] = useState('');
  const [manualError, setManualError] = useState(false);
  const lastScannedAt = useRef(0);
  const lastScannedBarcode = useRef<string | null>(null);
  const productQuery = useProductByBarcodeQuery(barcode);
  const refetchProduct = productQuery.refetch;
  const hasProductError = productQuery.isError;

  useEffect(() => {
    const productId = productQuery.data?.id;
    if (productId) {
      router.push({
        pathname: '/products/[productId]',
        params: { productId },
      } as unknown as Href);
    }
  }, [productQuery.data?.id, router]);

  const submitBarcode = useCallback(
    (value: string): void => {
      const normalized = normalizeBarcode(value);
      if (!normalized) {
        setManualError(true);
        return;
      }

      setManualError(false);
      if (normalized === barcode) {
        if (hasProductError) void refetchProduct();
        return;
      }
      setBarcode(normalized);
    },
    [barcode, hasProductError, refetchProduct],
  );

  const onBarcodeScanned = useCallback(
    (result: BarcodeScanningResult): void => {
      const normalized = normalizeBarcode(result.data);
      const now = Date.now();
      if (
        !normalized ||
        productQuery.isFetching ||
        normalized === lastScannedBarcode.current ||
        now - lastScannedAt.current < SCAN_DEBOUNCE_MS
      ) {
        return;
      }
      lastScannedAt.current = now;
      lastScannedBarcode.current = normalized;
      submitBarcode(normalized);
    },
    [productQuery.isFetching, submitBarcode],
  );

  const colorsStyle = {
    color: colors.text,
    backgroundColor: colors.surface,
    borderColor: colors.border,
  };

  return (
    <Screen contentContainerStyle={styles.content}>
      <Text accessibilityRole="header" style={[styles.title, { color: colors.text }]}>
        {t('scan.title')}
      </Text>
      {permission?.granted && isFocused ? (
        <View style={[styles.cameraFrame, { backgroundColor: colors.surfaceMuted }]}>
          <CameraView
            style={StyleSheet.absoluteFill}
            facing="back"
            enableTorch={torchEnabled}
            barcodeScannerSettings={{ barcodeTypes: [...BARCODE_TYPES] }}
            onBarcodeScanned={productQuery.isFetching ? undefined : onBarcodeScanned}
          />
          <View pointerEvents="none" style={styles.scanFrame} />
          <Pressable
            accessibilityRole="button"
            accessibilityLabel={torchEnabled ? t('scan.torch_off') : t('scan.torch_on')}
            accessibilityState={{ selected: torchEnabled }}
            onPress={() => setTorchEnabled((enabled) => !enabled)}
            style={({ pressed }) => [
              styles.torchButton,
              { backgroundColor: colors.primary, opacity: pressed ? 0.8 : 1 },
            ]}
          >
            <Text style={[styles.torchButtonText, { color: colors.onPrimary }]}>
              {torchEnabled ? '☼' : '◉'} {torchEnabled ? t('scan.torch_off') : t('scan.torch_on')}
            </Text>
          </Pressable>
        </View>
      ) : permission?.granted ? (
        <View style={[styles.cameraFrame, { backgroundColor: colors.surfaceMuted }]} />
      ) : permission ? (
        <View
          style={[
            styles.permissionCard,
            { backgroundColor: colors.surface, borderColor: colors.border },
          ]}
        >
          <Text style={[styles.bodyText, { color: colors.text }]}>{t('scan.camera_denied')}</Text>
          <ActionButton
            label={permission.canAskAgain ? t('scan.allow_camera') : t('scan.open_settings')}
            onPress={() => {
              if (permission.canAskAgain) void requestPermission();
              else void Linking.openSettings();
            }}
          />
        </View>
      ) : (
        <View style={styles.cameraLoading}>
          <Skeleton height={260} borderRadius={radii.lg} />
          <Text style={[styles.instruction, { color: colors.textMuted }]}>
            {t('scan.camera_loading')}
          </Text>
        </View>
      )}
      <Text style={[styles.instruction, { color: colors.textMuted }]}>{t('scan.instruction')}</Text>
      <Text style={[styles.manualLabel, { color: colors.text }]}>{t('scan.manual_label')}</Text>
      <View style={styles.entryRow}>
        <TextInput
          accessibilityLabel={t('scan.manual_label')}
          autoCapitalize="none"
          autoCorrect={false}
          keyboardType="number-pad"
          maxLength={20}
          onChangeText={(value) => {
            setManualBarcode(value);
            setManualError(false);
          }}
          onSubmitEditing={() => submitBarcode(manualBarcode)}
          placeholder={t('scan.manual_placeholder')}
          placeholderTextColor={colors.textMuted}
          returnKeyType="search"
          style={[styles.input, colorsStyle]}
          value={manualBarcode}
        />
        <ActionButton label={t('scan.lookup')} onPress={() => submitBarcode(manualBarcode)} />
      </View>
      {manualError ? (
        <Text accessibilityRole="alert" style={[styles.errorText, { color: colors.high }]}>
          {t('scan.enter_barcode')}
        </Text>
      ) : null}
      {productQuery.isFetching ? (
        <View accessibilityLiveRegion="polite" style={styles.statusRow}>
          <ActivityIndicator color={colors.primary} />
          <Text style={[styles.statusText, { color: colors.textMuted }]}>{t('scan.loading')}</Text>
        </View>
      ) : productQuery.error instanceof ApiError &&
        productQuery.error.type === PRODUCT_NOT_FOUND ? (
        <Text accessibilityRole="alert" style={[styles.errorText, { color: colors.high }]}>
          {t('scan.unknown_product')}
        </Text>
      ) : productQuery.error instanceof ApiError &&
        (productQuery.error.type === INVALID_BARCODE || productQuery.error.status === 422) ? (
        <Text accessibilityRole="alert" style={[styles.errorText, { color: colors.high }]}>
          {t('scan.invalid_barcode')}
        </Text>
      ) : productQuery.isError ? (
        <ErrorState
          title={t('errors.generic_title')}
          description={t('errors.generic_description')}
          buttonLabel={t('common.retry')}
          onRetry={() => void refetchProduct()}
        />
      ) : null}
    </Screen>
  );
}

interface ActionButtonProps {
  label: string;
  onPress: () => void;
}

function ActionButton({ label, onPress }: ActionButtonProps): ReactElement {
  const colors = useThemeColors();
  return (
    <Pressable
      accessibilityRole="button"
      onPress={onPress}
      style={({ pressed }) => [
        styles.actionButton,
        { backgroundColor: colors.primary, opacity: pressed ? 0.8 : 1 },
      ]}
    >
      <Text style={[styles.actionButtonText, { color: colors.onPrimary }]}>{label}</Text>
    </Pressable>
  );
}

function normalizeBarcode(value: string): string {
  return value.replace(/[\s-]/g, '');
}

const styles = StyleSheet.create({
  content: { padding: spacing.lg, gap: spacing.md },
  title: {
    marginBottom: spacing.sm,
    fontSize: typography.size.xl,
    lineHeight: typography.lineHeight.xl,
    fontWeight: typography.weight.bold,
  },
  cameraFrame: {
    height: 300,
    overflow: 'hidden',
    borderRadius: radii.lg,
    justifyContent: 'center',
    alignItems: 'center',
  },
  scanFrame: {
    width: '76%',
    height: 112,
    borderColor: '#FFFFFF',
    borderWidth: 3,
    borderRadius: radii.md,
  },
  torchButton: {
    position: 'absolute',
    right: spacing.md,
    bottom: spacing.md,
    minHeight: 48,
    justifyContent: 'center',
    paddingHorizontal: spacing.md,
    borderRadius: radii.pill,
  },
  torchButtonText: { fontSize: typography.size.sm, fontWeight: typography.weight.semibold },
  permissionCard: {
    minHeight: 190,
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing.lg,
    padding: spacing.xl,
    borderWidth: 1,
    borderRadius: radii.lg,
  },
  bodyText: {
    fontSize: typography.size.md,
    lineHeight: typography.lineHeight.md,
    textAlign: 'center',
  },
  cameraLoading: { gap: spacing.md },
  instruction: {
    marginTop: spacing.xs,
    fontSize: typography.size.sm,
    lineHeight: typography.lineHeight.sm,
    textAlign: 'center',
  },
  manualLabel: {
    marginTop: spacing.lg,
    fontSize: typography.size.md,
    fontWeight: typography.weight.semibold,
  },
  entryRow: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm },
  input: {
    flex: 1,
    minHeight: 52,
    borderWidth: 1,
    borderRadius: radii.md,
    paddingHorizontal: spacing.md,
    fontSize: typography.size.md,
  },
  actionButton: {
    minHeight: 48,
    minWidth: 108,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: spacing.md,
    borderRadius: radii.md,
  },
  actionButtonText: { fontSize: typography.size.sm, fontWeight: typography.weight.semibold },
  statusRow: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm, marginTop: spacing.sm },
  statusText: { fontSize: typography.size.sm },
  errorText: {
    marginTop: spacing.sm,
    fontSize: typography.size.md,
    lineHeight: typography.lineHeight.md,
  },
});
