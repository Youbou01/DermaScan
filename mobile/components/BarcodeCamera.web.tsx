import { View } from 'react-native';
import { ScanLine } from 'lucide-react-native';
import { AppText } from '@/components/AppText';
import { colors } from '@/lib/theme';
export type BarcodeCameraProps = { active: boolean; onScan: (code: string) => void };
export default function BarcodeCamera(_props: BarcodeCameraProps) {
  return (
    <View
      style={{
        height: 260,
        borderRadius: 22,
        backgroundColor: colors.peach,
        alignItems: 'center',
        justifyContent: 'center',
        padding: 26,
        gap: 18,
      }}
    >
      <ScanLine size={90} color={colors.ink} strokeWidth={1} />
      <AppText weight="semibold" style={{ fontSize: 19 }}>
        Your next discovery.
      </AppText>
      <AppText style={{ textAlign: 'center', lineHeight: 21, color: colors.ink }}>
        Camera scanning is available on iOS and Android. Enter a barcode below.
      </AppText>
    </View>
  );
}
