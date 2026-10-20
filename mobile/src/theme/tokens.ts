import { useColorScheme } from 'react-native';

export const lightColors = {
  background: '#F7F8F5',
  surface: '#FFFFFF',
  surfaceMuted: '#EEF1EC',
  text: '#17211B',
  textMuted: '#59665E',
  border: '#D7DED8',
  primary: '#246B50',
  onPrimary: '#FFFFFF',
  low: '#2F7657',
  lowSurface: '#E6F2EB',
  moderate: '#8A5A00',
  moderateSurface: '#FFF2D6',
  high: '#A13E3E',
  highSurface: '#FBE9E7',
  unknown: '#56616D',
  unknownSurface: '#E9EDF1',
  skeleton: '#DDE3DE',
} as const;

export const darkColors: Record<keyof typeof lightColors, string> = {
  background: '#111713',
  surface: '#1A231D',
  surfaceMuted: '#263129',
  text: '#F0F5F1',
  textMuted: '#B4C0B7',
  border: '#3A4840',
  primary: '#8BC6A5',
  onPrimary: '#102016',
  low: '#9AD0AE',
  lowSurface: '#203B2C',
  moderate: '#F0C875',
  moderateSurface: '#3A301C',
  high: '#F0A19B',
  highSurface: '#402523',
  unknown: '#C0CBD5',
  unknownSurface: '#29333D',
  skeleton: '#354139',
};

export type ThemeColors = Record<keyof typeof lightColors, string>;
export type RiskToken = 'low' | 'moderate' | 'high' | 'unknown';

export const typography = {
  family: { regular: 'System', medium: 'System', semibold: 'System', bold: 'System' },
  size: { xs: 12, sm: 14, md: 16, lg: 20, xl: 28, display: 34 },
  lineHeight: { xs: 16, sm: 20, md: 24, lg: 28, xl: 36 },
  letterSpacing: { tight: -0.4, normal: 0, wide: 0.6 },
  weight: { regular: '400', medium: '500', semibold: '600', bold: '700' } as const,
};

export const spacing = {
  none: 0,
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 24,
  xxl: 32,
  xxxl: 48,
} as const;
export const radii = { sm: 8, md: 12, lg: 18, pill: 999 } as const;

export function useThemeColors(): ThemeColors {
  return useColorScheme() === 'dark' ? darkColors : lightColors;
}
