import type { ReactElement } from 'react';
import { StyleSheet, Text, View } from 'react-native';

// Placeholder until MOB-06 (Home). Text is hard-coded only until MOB-03 introduces i18n.
export const FOUNDATION_TITLE = 'Skincare';

export default function HomeRoute(): ReactElement {
  return (
    <View style={styles.container}>
      <Text accessibilityRole="header" style={styles.title}>
        {FOUNDATION_TITLE}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  title: { fontSize: 28, fontWeight: '600' },
});
