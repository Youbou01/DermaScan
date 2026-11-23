import { Typography } from 'heroui-native';
import type { ComponentProps } from 'react';
import { colors } from '@/lib/theme';

type Props = Omit<ComponentProps<typeof Typography>, 'weight'> & {
  weight?: 'regular' | 'medium' | 'semibold' | 'bold';
};
const fonts = {
  regular: 'Inter_400Regular',
  medium: 'Inter_500Medium',
  semibold: 'Inter_600SemiBold',
  bold: 'Inter_700Bold',
};
export function AppText({ weight = 'regular', style, ...props }: Props) {
  return (
    <Typography
      {...props}
      style={[{ fontFamily: fonts[weight], color: colors.ink, fontSize: 14 }, style]}
    />
  );
}
