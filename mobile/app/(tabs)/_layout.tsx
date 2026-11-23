import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { colors } from '@/lib/theme';
export default function HomeLayout() {
  return (
    <>
      {/* eslint-disable-next-line react/style-prop-object -- Expo StatusBar style is a string enum, not a React Native style object. */}
      <StatusBar style="dark" />
      <Stack
        screenOptions={{ headerShown: false, contentStyle: { backgroundColor: colors.background } }}
      />
    </>
  );
}
