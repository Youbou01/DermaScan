import { useEffect, useState, type ReactElement } from 'react';
import { AccessibilityInfo, Animated, View } from 'react-native';
import { useTheme } from '@/theme/theme';
import { useI18n } from '@/i18n';
export interface SkeletonProps {
  readonly variant?: 'block' | 'line' | 'product';
  readonly reduceMotion?: boolean;
}
export function Skeleton({ variant = 'block', reduceMotion = false }: SkeletonProps): ReactElement {
  const { colors, radius } = useTheme();
  const { t } = useI18n();
  const [systemReduceMotion, setSystemReduceMotion] = useState(false);
  const [opacity] = useState(() => new Animated.Value(0.55));
  const motionDisabled = reduceMotion || systemReduceMotion;
  useEffect(() => {
    let mounted = true;
    void AccessibilityInfo.isReduceMotionEnabled().then((enabled) => {
      if (mounted) setSystemReduceMotion(enabled);
    });
    const subscription = AccessibilityInfo.addEventListener(
      'reduceMotionChanged',
      setSystemReduceMotion,
    );
    return () => {
      mounted = false;
      subscription.remove();
    };
  }, []);
  useEffect(() => {
    if (motionDisabled) {
      opacity.setValue(1);
      return;
    }
    const pulse = Animated.loop(
      Animated.sequence([
        Animated.timing(opacity, { toValue: 0.3, duration: 900, useNativeDriver: true }),
        Animated.timing(opacity, { toValue: 0.7, duration: 900, useNativeDriver: true }),
      ]),
    );
    pulse.start();
    return () => pulse.stop();
  }, [motionDisabled, opacity]);
  const blockStyle = { backgroundColor: colors.border, borderRadius: radius.sm };
  return (
    <Animated.View
      accessibilityRole="progressbar"
      accessibilityLabel={t('loading')}
      accessibilityState={{ busy: true }}
      style={{
        opacity,
        gap: 10,
        padding: variant === 'product' ? 16 : 0,
        borderRadius: radius.md,
        backgroundColor: variant === 'product' ? colors.surface : 'transparent',
      }}
    >
      <View
        style={[
          blockStyle,
          { width: variant === 'line' ? '70%' : 80, height: variant === 'line' ? 14 : 80 },
        ]}
      />
      {variant === 'product' ? (
        <>
          <View style={[blockStyle, { height: 16, width: '80%' }]} />
          <View style={[blockStyle, { height: 14, width: '55%' }]} />
        </>
      ) : null}
    </Animated.View>
  );
}
