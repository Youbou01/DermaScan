import { useState } from 'react';
import { View, Linking } from 'react-native';
import { CameraView, useCameraPermissions } from 'expo-camera';
import { Button } from 'heroui-native';
import { Camera, ScanLine } from 'lucide-react-native';
import { AppText } from '@/components/AppText';
import { colors } from '@/lib/theme';
import * as Haptics from 'expo-haptics';
export type BarcodeCameraProps = { active: boolean; onScan: (code: string) => void };
export default function BarcodeCamera({ active, onScan }: BarcodeCameraProps) {
  const [permission, requestPermission] = useCameraPermissions();
  const [error, setError] = useState(false);
  const [pending, setPending] = useState(false);
  const allow = async () => {
    setPending(true);
    try {
      await requestPermission();
    } catch {
      setError(true);
      void Haptics.notificationAsync(Haptics.NotificationFeedbackType.Error);
    } finally {
      setPending(false);
    }
  };
  if (!permission?.granted || error)
    return (
      <View
        style={{
          height: 280,
          alignItems: 'center',
          justifyContent: 'center',
          padding: 22,
          gap: 18,
          borderRadius: 22,
          backgroundColor: colors.blue,
        }}
      >
        <Camera size={40} color={colors.ink} strokeWidth={1.8} />
        <AppText style={{ textAlign: 'center' }}>
          {error
            ? 'Camera access failed. Please try again.'
            : 'Allow camera access to scan a barcode.'}
        </AppText>
        <Button
          isDisabled={pending}
          onPress={() => {
            if (permission && !permission.canAskAgain) void Linking.openSettings();
            else {
              setError(false);
              void allow();
            }
          }}
        >
          <Button.Label>
            {pending
              ? 'Opening camera…'
              : permission && !permission.canAskAgain
                ? 'Open settings'
                : error
                  ? 'Try again'
                  : 'Enable camera'}
          </Button.Label>
        </Button>
      </View>
    );
  return (
    <View
      style={{ height: 280, borderRadius: 22, overflow: 'hidden', backgroundColor: colors.ink }}
    >
      <CameraView
        style={{ flex: 1 }}
        facing="back"
        barcodeScannerSettings={{ barcodeTypes: ['ean13', 'ean8', 'upc_a', 'upc_e', 'code128'] }}
        onBarcodeScanned={active ? ({ data }) => onScan(data) : undefined}
        onMountError={() => {
          setError(true);
          void Haptics.notificationAsync(Haptics.NotificationFeedbackType.Error);
        }}
      />
      <View
        pointerEvents="none"
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <ScanLine size={160} color={colors.white} strokeWidth={1} />
      </View>
    </View>
  );
}
