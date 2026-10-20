import type { ReactElement } from 'react';
<<<<<<< HEAD
import { useRouter, type Href } from 'expo-router';
import { Pressable, StyleSheet, Text, View } from 'react-native';

// Placeholder until MOB-06 (Home). Text is hard-coded only until MOB-03 introduces i18n.
export const FOUNDATION_TITLE = 'Skincare';

export default function HomeRoute(): ReactElement {
  const router = useRouter();
  return (
    <View style={styles.container}>
      <Text accessibilityRole="header" style={styles.title}>
        {FOUNDATION_TITLE}
      </Text>
      <Pressable
        accessibilityRole="button"
        onPress={() => router.push('/scan' as Href)}
        style={styles.button}
      >
        <Text style={styles.buttonText}>Scan a product</Text>
      </Pressable>
      {__DEV__ ? (
        <Pressable
          accessibilityRole="button"
          onPress={() => router.push('/design-system' as Href)}
          style={[styles.button, styles.showcaseButton]}
        >
          <Text style={styles.buttonText}>Open design system showcase</Text>
        </Pressable>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  title: { fontSize: 28, fontWeight: '600' },
  button: {
    minHeight: 48,
    marginTop: 20,
    paddingHorizontal: 20,
    justifyContent: 'center',
    borderRadius: 14,
    backgroundColor: '#244f43',
  },
  showcaseButton: { backgroundColor: '#246B50' },
  buttonText: { color: '#fff', fontSize: 16, fontWeight: '600' },
});
=======
import { HomeScreen } from '@/features/home/HomeScreen';

export default function HomeRoute(): ReactElement {
  return <HomeScreen />;
}
>>>>>>> main
