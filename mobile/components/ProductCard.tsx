import { View } from 'react-native';
import { PressableFeedback } from 'heroui-native';
import { router } from 'expo-router';
import { AppText } from '@/components/AppText';
import { ProductPhoto } from '@/components/ProductPhoto';
import { ScoreBadge } from '@/components/ScoreBadge';
import type { Product } from '@/lib/api/types';
import { colors } from '@/lib/theme';
export function ProductCard({ product }: { product: Product }) {
  return (
    <PressableFeedback
      accessibilityRole="button"
      accessibilityLabel={`View ${product.name}`}
      onPress={() => router.push({ pathname: '/product/[id]', params: { id: product.id } })}
      style={{ flex: 1 }}
    >
      <ProductPhoto url={product.image_url} name={product.name} />
      <View style={{ paddingTop: 11, gap: 5 }}>
        <View style={{ minHeight: 16 }}>
          {!!product.brand && (
            <AppText
              weight="semibold"
              numberOfLines={1}
              style={{ fontSize: 11, lineHeight: 16, color: colors.muted }}
            >
              {product.brand}
            </AppText>
          )}
        </View>
        <AppText
          weight="semibold"
          numberOfLines={2}
          style={{ fontSize: 14, lineHeight: 20, minHeight: 40 }}
        >
          {product.name}
        </AppText>
        <View style={{ alignItems: 'flex-start', marginTop: 3 }}>
          <ScoreBadge score={product.score} band={product.score_band} />
        </View>
      </View>
    </PressableFeedback>
  );
}
