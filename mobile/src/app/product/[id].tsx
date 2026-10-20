import { useLocalSearchParams } from 'expo-router';
import type { ReactElement } from 'react';
import { ActivityIndicator, StyleSheet, Text, View } from 'react-native';
import { useProductQuery } from '@/api/hooks';

export default function ProductRoute(): ReactElement {
  const { id } = useLocalSearchParams<{ id: string }>();
  const productQuery = useProductQuery(id);

  if (productQuery.isPending) {
    return <ActivityIndicator accessibilityLabel="Loading product" style={styles.centered} />;
  }

  if (productQuery.error || !productQuery.data) {
    return (
      <View style={styles.centered}>
        <Text style={styles.title}>Product details</Text>
      </View>
    );
  }

  return (
    <View style={styles.centered}>
      <Text accessibilityRole="header" style={styles.title}>
        {productQuery.data.name}
      </Text>
      {productQuery.data.brand ? <Text style={styles.body}>{productQuery.data.brand}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  centered: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 24,
    backgroundColor: '#f7f5f2',
  },
  title: { fontSize: 26, fontWeight: '700', color: '#192b27', textAlign: 'center' },
  body: { marginTop: 8, fontSize: 17, color: '#51635d' },
});
