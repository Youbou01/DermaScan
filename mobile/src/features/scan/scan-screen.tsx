import { CameraView, useCameraPermissions, type BarcodeScanningResult } from 'expo-camera';
import { useRouter, type Href } from 'expo-router';
import { useCallback, useEffect, useRef, useState, type ReactElement } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text, TextInput, View } from 'react-native';
import { ApiError } from '@/api/errors';
import { useProductByBarcodeQuery } from '@/api/hooks';
import { getActiveApiLocale } from '@/api/locale';

const COPY = {
  en: {
    title: 'Scan a product',
    instruction: 'Place the barcode inside the frame',
    permission: 'Camera access is needed to scan a product barcode.',
    allow: 'Allow camera',
    denied: 'Camera access is off. You can enter the barcode manually.',
    manual: 'Enter barcode manually',
    lookup: 'Look up product',
    torchOn: 'Turn torch on',
    torchOff: 'Turn torch off',
    unknown: "We don't know this product yet.",
    invalid: 'Check the barcode and try again.',
    error: 'We could not look up this product. Try again.',
    loading: 'Looking up product…',
  },
  fr: {
    title: 'Scanner un produit',
    instruction: 'Placez le code-barres dans le cadre',
    permission: 'L’accès à la caméra est nécessaire pour scanner un code-barres.',
    allow: 'Autoriser la caméra',
    denied: 'L’accès à la caméra est désactivé. Saisissez le code-barres manuellement.',
    manual: 'Saisir le code-barres',
    lookup: 'Rechercher le produit',
    torchOn: 'Allumer la lampe',
    torchOff: 'Éteindre la lampe',
    unknown: 'Nous ne connaissons pas encore ce produit.',
    invalid: 'Vérifiez le code-barres et réessayez.',
    error: 'Impossible de rechercher ce produit. Réessayez.',
    loading: 'Recherche du produit…',
  },
} as const;

const BARCODE_TYPES = ['ean13', 'ean8', 'upc_a'] as const;
const SCAN_DEBOUNCE_MS = 1800;

export function ScanScreen(): ReactElement {
  const router = useRouter();
  const [permission, requestPermission] = useCameraPermissions();
  const [torchEnabled, setTorchEnabled] = useState(false);
  const [barcode, setBarcode] = useState<string | undefined>();
  const [manualBarcode, setManualBarcode] = useState('');
  const [message, setMessage] = useState<string | undefined>();
  const lastScannedAt = useRef(0);
  const copy = COPY[getActiveApiLocale()];
  const productQuery = useProductByBarcodeQuery(barcode);

  useEffect(() => {
    if (productQuery.data) {
      router.push({
        pathname: '/product/[id]',
        params: { id: productQuery.data.id },
      } as unknown as Href);
    }
  }, [productQuery.data, router]);

  const lookup = useCallback((value: string): void => {
    const normalized = value.replace(/[\s-]/g, '');
    if (!normalized) return;
    setMessage(undefined);
    setBarcode(normalized);
  }, []);

  const onBarcodeScanned = useCallback(
    (result: BarcodeScanningResult): void => {
      const now = Date.now();
      if (productQuery.isFetching || now - lastScannedAt.current < SCAN_DEBOUNCE_MS) return;
      lastScannedAt.current = now;
      lookup(result.data);
    },
    [lookup, productQuery.isFetching],
  );

  return (
    <View style={styles.container}>
      <Text accessibilityRole="header" style={styles.title}>
        {copy.title}
      </Text>
      {permission?.granted ? (
        <View style={styles.cameraFrame}>
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
            accessibilityLabel={torchEnabled ? copy.torchOff : copy.torchOn}
            accessibilityState={{ selected: torchEnabled }}
            onPress={() => setTorchEnabled((enabled) => !enabled)}
            style={styles.torchButton}
          >
            <Text style={styles.buttonText}>{torchEnabled ? '☼  ON' : '☼  OFF'}</Text>
          </Pressable>
        </View>
      ) : (
        <View style={styles.permissionCard}>
          <Text style={styles.bodyText}>{permission ? copy.denied : copy.permission}</Text>
          {permission && !permission.granted ? (
            <ActionButton label={copy.allow} onPress={() => void requestPermission()} />
          ) : null}
        </View>
      )}
      <Text style={styles.instruction}>{copy.instruction}</Text>
      <Text style={styles.manualLabel}>{copy.manual}</Text>
      <View style={styles.entryRow}>
        <TextInput
          accessibilityLabel={copy.manual}
          keyboardType="number-pad"
          value={manualBarcode}
          onChangeText={setManualBarcode}
          onSubmitEditing={() => lookup(manualBarcode)}
          style={styles.input}
          maxLength={20}
          returnKeyType="search"
        />
        <ActionButton label={copy.lookup} onPress={() => lookup(manualBarcode)} />
      </View>
      {productQuery.isFetching ? (
        <View accessibilityLiveRegion="polite" style={styles.statusRow}>
          <ActivityIndicator />
          <Text style={styles.statusText}>{copy.loading}</Text>
        </View>
      ) : productQuery.error instanceof ApiError ? (
        <Text accessibilityRole="alert" style={styles.errorText}>
          {productQuery.error.type === 'urn:skincare:problem:product-not-found'
            ? copy.unknown
            : productQuery.error.type === 'urn:skincare:problem:invalid-barcode' ||
                productQuery.error.status === 422
              ? copy.invalid
              : copy.error}
        </Text>
      ) : message ? (
        <Text accessibilityRole="alert" style={styles.errorText}>
          {message}
        </Text>
      ) : null}
    </View>
  );
}

function ActionButton({ label, onPress }: { label: string; onPress: () => void }): ReactElement {
  return (
    <Pressable accessibilityRole="button" onPress={onPress} style={styles.actionButton}>
      <Text style={styles.buttonText}>{label}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, paddingHorizontal: 24, paddingTop: 64, backgroundColor: '#f7f5f2' },
  title: { color: '#192b27', fontSize: 28, fontWeight: '700', marginBottom: 20 },
  cameraFrame: {
    height: 330,
    overflow: 'hidden',
    borderRadius: 28,
    backgroundColor: '#182722',
    justifyContent: 'center',
    alignItems: 'center',
  },
  scanFrame: { width: '72%', height: 120, borderColor: '#fff', borderWidth: 3, borderRadius: 18 },
  torchButton: {
    position: 'absolute',
    bottom: 14,
    right: 14,
    minHeight: 48,
    minWidth: 76,
    borderRadius: 24,
    paddingHorizontal: 14,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: 'rgba(20, 36, 32, 0.82)',
  },
  permissionCard: {
    minHeight: 190,
    borderRadius: 28,
    padding: 24,
    justifyContent: 'center',
    alignItems: 'center',
    gap: 18,
    backgroundColor: '#e9eee9',
  },
  bodyText: { color: '#263a34', fontSize: 16, lineHeight: 24, textAlign: 'center' },
  instruction: { marginTop: 16, color: '#51635d', fontSize: 15, textAlign: 'center' },
  manualLabel: {
    marginTop: 30,
    marginBottom: 10,
    color: '#263a34',
    fontSize: 16,
    fontWeight: '600',
  },
  entryRow: { flexDirection: 'row', gap: 10 },
  input: {
    flex: 1,
    minHeight: 52,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: '#c8d0ca',
    paddingHorizontal: 14,
    color: '#192b27',
    fontSize: 17,
    backgroundColor: '#fff',
  },
  actionButton: {
    minHeight: 48,
    minWidth: 108,
    borderRadius: 14,
    paddingHorizontal: 16,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#244f43',
  },
  buttonText: { color: '#fff', fontSize: 15, fontWeight: '600', textAlign: 'center' },
  statusRow: { flexDirection: 'row', alignItems: 'center', gap: 10, marginTop: 18 },
  statusText: { color: '#51635d', fontSize: 15 },
  errorText: { marginTop: 18, color: '#8b3028', fontSize: 16, lineHeight: 24 },
});
