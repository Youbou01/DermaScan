import type { ReactElement } from 'react';
import { Link } from 'expo-router';
import { Pressable, StyleSheet, Text, View } from 'react-native';

// Placeholder until MOB-06 (Home). Text is hard-coded only until MOB-03 introduces i18n.
export const FOUNDATION_TITLE = 'Skincare';

export default function HomeRoute(): ReactElement {
  return (
    <View style={styles.container}>
      <Text accessibilityRole="header" style={styles.title}>
        {FOUNDATION_TITLE}
      </Text>
      {__DEV__ ? (
        <Link href="/design-system" asChild>
          <Pressable accessibilityRole="button" style={styles.showcaseButton}>
            <Text style={styles.showcaseText}>Open design system showcase</Text>
          </Pressable>
        </Link>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  title: { fontSize: 28, fontWeight: '600' },
  showcaseButton: {
    minHeight: 44,
    marginTop: 20,
    justifyContent: 'center',
    paddingHorizontal: 16,
    borderRadius: 12,
    backgroundColor: '#246B50',
  },
  showcaseText: { color: '#FFFFFF', fontSize: 16, fontWeight: '600' },
});
