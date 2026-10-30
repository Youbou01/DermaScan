import { memo, useCallback, type ReactElement } from 'react';
import { Image, Pressable, StyleSheet, Text, View } from 'react-native';
import type { HomeSection } from '@/api/types';
import { getLocalizedCategory } from '@/i18n/category';
import { useTranslation } from '@/i18n/useTranslation';
import { radii, spacing, typography, useThemeColors } from '@/theme/tokens';
import { getProductArtwork } from '../product-artwork';

interface CategoryGridProps {
  section: HomeSection;
  onCategoryPress: (slug: string) => void;
}

function CategoryGridView({ section, onCategoryPress }: CategoryGridProps): ReactElement {
  const colors = useThemeColors();
  const { t } = useTranslation();
  const categories = section.items.filter((item) => 'slug' in item);
  const renderCategory = useCallback(
    (category: (typeof categories)[number]): ReactElement => {
      const name = getLocalizedCategory(category);
      return (
        <Pressable
          key={category.slug}
          accessibilityRole="button"
          accessibilityLabel={t('home.category_accessibility', { name })}
          onPress={() => onCategoryPress(category.slug)}
          style={({ pressed }) => [
            styles.tile,
            {
              backgroundColor: colors.surface,
              borderColor: colors.border,
              opacity: pressed ? 0.75 : 1,
            },
          ]}
        >
          {getProductArtwork(category.slug) ? (
            <Image
              accessibilityElementsHidden
              source={getProductArtwork(category.slug)}
              style={styles.image}
            />
          ) : null}
          <Text style={[styles.label, { color: colors.text }]}>{name}</Text>
        </Pressable>
      );
    },
    [colors.border, colors.surface, colors.text, onCategoryPress, t],
  );
  const rows: (typeof categories)[] = [];
  for (let index = 0; index < categories.length; index += 2) {
    rows.push(categories.slice(index, index + 2));
  }
  return (
    <View style={styles.container}>
      <Text accessibilityRole="header" style={[styles.title, { color: colors.text }]}>
        {section.title}
      </Text>
      <View style={styles.grid}>{rows.map((row) => row.map(renderCategory))}</View>
    </View>
  );
}

export const CategoryGrid = memo(CategoryGridView);

const styles = StyleSheet.create({
  container: { gap: spacing.md, padding: spacing.lg },
  title: { fontSize: typography.size.lg, lineHeight: typography.lineHeight.lg, fontWeight: '700' },
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.md },
  tile: {
    width: '47%',
    minHeight: 76,
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    padding: spacing.md,
    justifyContent: 'center',
    borderWidth: 1,
    borderRadius: radii.md,
  },
  image: { width: 44, height: 44, borderRadius: radii.sm },
  label: { fontSize: typography.size.md, lineHeight: typography.lineHeight.md, fontWeight: '600' },
});
