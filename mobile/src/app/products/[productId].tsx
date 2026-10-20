import type { ReactElement } from 'react';
import { useLocalSearchParams } from 'expo-router';
import { ProductDetailScreen } from '@/features/product/product-detail-screen';

export default function ProductDetailRoute(): ReactElement {
  const { productId } = useLocalSearchParams<{ productId?: string | string[] }>();
  const normalizedProductId = Array.isArray(productId) ? productId[0] : productId;
  return <ProductDetailScreen productId={normalizedProductId} />;
}
