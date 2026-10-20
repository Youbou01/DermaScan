import { Link } from 'expo-router';
import type { ReactElement } from 'react';
import { StyleSheet, Text, View } from 'react-native';

// Reached for unknown deep links. Replaced by the shared ErrorState in MOB-10.
export default function NotFoundRoute(): ReactElement {
  return (
    <View style={styles.container}>
      <Text accessibilityRole="header" style={styles.title}>
        This screen does not exist.
      </Text>
      <Link href="/" style={styles.link}>
        Go to the home screen
      </Link>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 24, gap: 16 },
  title: { fontSize: 20, fontWeight: '600', textAlign: 'center' },
  link: { fontSize: 16, minHeight: 44, paddingVertical: 12 },
});
