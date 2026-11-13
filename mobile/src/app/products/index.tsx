import type { ReactElement } from 'react';
import { useLocalSearchParams } from 'expo-router';
import { ProductCatalogScreen } from '@/features/search/ProductCatalogScreen';

export default function ProductsCatalogRoute(): ReactElement {
  const { category } = useLocalSearchParams<{ category?: string | string[] }>();
  const normalizedCategory = Array.isArray(category) ? category[0] : category;
  return <ProductCatalogScreen initialCategory={normalizedCategory} />;
}
