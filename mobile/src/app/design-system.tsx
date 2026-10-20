import { router } from 'expo-router';
import { useState } from 'react';
import type { ReactElement } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import {
  EmptyState,
  ErrorState,
  ProductCard,
  RiskBadge,
  ScoreBadge,
  Screen,
  Skeleton,
} from '@/components';
import { productFixture } from '@/api/fixtures';
import type { RiskLevel } from '@/api/types';
import { spacing, typography, useThemeColors } from '@/theme/tokens';

const levels: RiskLevel[] = ['low', 'moderate', 'high', 'unknown'];
const product = {
  id: 'demo-product',
  name: 'Daily Hydrating Face Cream',
  brand: 'DermaScan Studio',
  image_url: null,
  score: 82,
  score_band: 'low' as const,
  category_slug: 'moisturizers',
};

export default function DesignSystemShowcase(): ReactElement | null {
  const [grayscale, setGrayscale] = useState(false);
  const [message, setMessage] = useState('');
  const colors = useThemeColors();
  if (!__DEV__) return null;
  return (
    <Screen contentContainerStyle={styles.content}>
      <Text accessibilityRole="header" style={[styles.title, { color: colors.text }]}>
        Design system
      </Text>
      <Text style={[styles.section, { color: colors.text }]}>Risk indicators</Text>
      <Pressable
        accessibilityRole="switch"
        accessibilityState={{ checked: grayscale }}
        onPress={() => setGrayscale(!grayscale)}
        style={[styles.toggle, { borderColor: colors.border }]}
      >
        <Text style={{ color: colors.text }}>{grayscale ? '✓ ' : ''}Grayscale preview</Text>
      </Pressable>
      <View style={styles.wrap}>
        {levels.map((level) => (
          <RiskBadge key={level} level={level} grayscale={grayscale} />
        ))}
      </View>
      <Text style={[styles.section, { color: colors.text }]}>Score tiers</Text>
      <View style={styles.wrap}>
        <ScoreBadge score={91} />
        <ScoreBadge score={58} />
        <ScoreBadge score={21} />
        <ScoreBadge score={null} />
      </View>
      <Text style={[styles.section, { color: colors.text }]}>Product cards</Text>
      <ProductCard product={product} onPress={(id) => setMessage(`Selected ${id}`)} />
      <ProductCard
        product={{
          ...product,
          id: 'missing-image',
          name: 'Product with missing image and a deliberately long name to check wrapping',
          brand: null,
          score: null,
          score_band: null,
          category_slug: null,
        }}
        onPress={(id) => setMessage(`Selected ${id}`)}
      />
      <Pressable
        accessibilityRole="button"
        onPress={() =>
          router.push({
            pathname: '/products/[productId]',
            params: { productId: productFixture.id },
          })
        }
        style={[styles.action, { backgroundColor: colors.primary }]}
      >
        <Text style={{ color: colors.onPrimary }}>Open sample product details</Text>
      </Pressable>
      <Text style={[styles.section, { color: colors.text }]}>Loading placeholders</Text>
      <Skeleton variant="text" width="62%" />
      <View style={styles.row}>
        <Skeleton variant="circle" width={56} height={56} />
        <View style={styles.flex}>
          <Skeleton variant="text" />
          <Skeleton variant="text" width="72%" />
        </View>
      </View>
      <Skeleton variant="rect" height={120} borderRadius={20} />
      <Text style={[styles.section, { color: colors.text }]}>Error and empty states</Text>
      <ErrorState
        title="Could not load preview"
        description="Check your connection and try again."
        onRetry={() => setMessage('Retry action triggered')}
        buttonLabel="Retry"
      />
      <EmptyState
        title="No products yet"
        description="Scan a product to see its ingredient risk indicators."
        action={
          <Pressable
            accessibilityRole="button"
            onPress={() => setMessage('Empty state action triggered')}
            style={[styles.action, { backgroundColor: colors.primary }]}
          >
            <Text style={{ color: colors.onPrimary }}>Scan a product</Text>
          </Pressable>
        }
      />
      {message ? (
        <Text accessibilityRole="status" style={[styles.message, { color: colors.primary }]}>
          {message}
        </Text>
      ) : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  content: { padding: spacing.lg, gap: spacing.md },
  title: {
    fontSize: typography.size.xl,
    lineHeight: typography.lineHeight.xl,
    fontWeight: typography.weight.bold,
  },
  section: {
    marginTop: spacing.lg,
    fontSize: typography.size.lg,
    lineHeight: typography.lineHeight.lg,
    fontWeight: typography.weight.semibold,
  },
  wrap: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm },
  toggle: {
    minHeight: 44,
    alignSelf: 'flex-start',
    justifyContent: 'center',
    paddingHorizontal: spacing.md,
    borderWidth: 1,
    borderRadius: 8,
  },
  row: { flexDirection: 'row', gap: spacing.md },
  flex: { flex: 1, justifyContent: 'center', gap: spacing.sm },
  action: {
    minHeight: 44,
    justifyContent: 'center',
    paddingHorizontal: spacing.lg,
    borderRadius: 12,
  },
  message: { padding: spacing.md, fontWeight: typography.weight.semibold },
});
