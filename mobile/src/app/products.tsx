import type { ReactElement } from 'react';
import { useLocalSearchParams } from 'expo-router';
import { ProductList, Screen } from '@/components';

function firstParam(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}

/** /products?category=serum (category tap) or /products?q=cream (search results). */
export default function ProductsRoute(): ReactElement {
  const params = useLocalSearchParams<{ category?: string; q?: string }>();
  return (
    <Screen scroll={false}>
      <ProductList category={firstParam(params.category)} query={firstParam(params.q)} />
    </Screen>
  );
}
