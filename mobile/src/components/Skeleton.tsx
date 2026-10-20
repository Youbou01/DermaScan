import type { ReactElement } from 'react';
import { useEffect, useState } from 'react';
import { Animated, Easing, StyleSheet } from 'react-native';
import { radii, useThemeColors } from '@/theme/tokens';

export interface SkeletonProps {
  variant?: 'rect' | 'circle' | 'text';
  width?: number | `${number}%`;
  height?: number;
  borderRadius?: number;
}

export function Skeleton({
  variant = 'rect',
  width = '100%',
  height = variant === 'text' ? 16 : 80,
  borderRadius,
}: SkeletonProps): ReactElement {
  const colors = useThemeColors();
  const [opacity] = useState(() => new Animated.Value(0.55));
  useEffect(() => {
    const pulse = Animated.loop(
      Animated.sequence([
        Animated.timing(opacity, {
          toValue: 1,
          duration: 850,
          easing: Easing.inOut(Easing.ease),
          useNativeDriver: true,
        }),
        Animated.timing(opacity, {
          toValue: 0.55,
          duration: 850,
          easing: Easing.inOut(Easing.ease),
          useNativeDriver: true,
        }),
      ]),
    );
    pulse.start();
    return () => pulse.stop();
  }, [opacity]);
  const radius =
    borderRadius ?? (variant === 'circle' ? radii.pill : variant === 'text' ? radii.sm : radii.md);
  return (
    <Animated.View
      accessibilityRole="progressbar"
      accessibilityLabel="Loading"
      style={[
        styles.skeleton,
        { width, height, borderRadius: radius, backgroundColor: colors.skeleton, opacity },
      ]}
    />
  );
}

const styles = StyleSheet.create({ skeleton: { opacity: 0.8 } });
