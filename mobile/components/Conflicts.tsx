import { View } from 'react-native';
import { AppText } from './AppText';
import { colors } from '@/lib/theme';
import type { Conflict } from '@/lib/api/types';
export function Conflicts({ conflicts }: { conflicts: Conflict[] }) {
  return (
    <View style={{ gap: 16 }}>
      {conflicts.map((conflict) => (
        <View
          key={JSON.stringify([
            conflict.code,
            conflict.product_a_id,
            conflict.product_b_id,
            conflict.ingredient_a,
            conflict.ingredient_b,
          ])}
          style={{ borderTopWidth: 1, borderTopColor: colors.border, paddingTop: 14, gap: 8 }}
        >
          <AppText
            weight="semibold"
            style={{ color: conflict.severity === 'high' ? colors.red : colors.orange }}
          >
            {conflict.title}
          </AppText>
          <AppText style={{ fontSize: 12, color: colors.muted }}>
            {conflict.product_a_name} + {conflict.product_b_name}
          </AppText>
          <AppText style={{ lineHeight: 21 }}>{conflict.detail}</AppText>
          <AppText weight="medium" style={{ lineHeight: 21 }}>
            {conflict.resolution}
          </AppText>
        </View>
      ))}
    </View>
  );
}
