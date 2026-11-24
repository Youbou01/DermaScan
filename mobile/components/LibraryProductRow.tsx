import { View } from 'react-native';
import { PressableFeedback, Button } from 'heroui-native';
import { router } from 'expo-router';
import { useTranslation } from 'react-i18next';
import { AppText } from '@/components/AppText';
import { ProductPhoto } from '@/components/ProductPhoto';
import { ScoreBadge } from '@/components/ScoreBadge';
import type { ProductCard } from '@/lib/api/types';
import { colors } from '@/lib/theme';

export function LibraryProductRow({
  product,
  actionLabel,
  onAction,
  isDisabled = false,
}: {
  product: ProductCard;
  actionLabel?: string;
  onAction?: () => void;
  isDisabled?: boolean;
}) {
  const { t } = useTranslation();

  return (
    <View
      style={{
        flexDirection: 'row',
        alignItems: 'center',
        gap: 12,
        borderBottomWidth: 1,
        borderBottomColor: colors.border,
        paddingVertical: 12,
      }}
    >
      <PressableFeedback
        accessibilityRole="button"
        accessibilityLabel={t('library.viewProduct', { name: product.name })}
        onPress={() => router.push({ pathname: '/product/[id]', params: { id: product.id } })}
        style={{ flex: 1, minHeight: 64, flexDirection: 'row', alignItems: 'center', gap: 12 }}
      >
        <View style={{ width: 74 }}>
          <ProductPhoto url={product.image_url} name={product.name} height={74} />
        </View>
        <View style={{ flex: 1, gap: 5 }}>
          {!!product.brand && (
            <AppText numberOfLines={1} style={{ color: colors.muted, fontSize: 11 }}>
              {product.brand}
            </AppText>
          )}
          <AppText weight="semibold" numberOfLines={2} style={{ lineHeight: 19 }}>
            {product.name}
          </AppText>
          <View style={{ alignSelf: 'flex-start' }}>
            <ScoreBadge score={product.score} band={product.score_band} />
          </View>
        </View>
      </PressableFeedback>
      {onAction && actionLabel && (
        <Button
          size="sm"
          variant="tertiary"
          isDisabled={isDisabled}
          accessibilityLabel={actionLabel}
          onPress={onAction}
          style={{ minHeight: 44, paddingHorizontal: 8 }}
        >
          <Button.Label numberOfLines={2} style={{ fontSize: 11 }}>
            {actionLabel}
          </Button.Label>
        </Button>
      )}
    </View>
  );
}
