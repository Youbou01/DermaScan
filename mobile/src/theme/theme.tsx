import { createContext, useContext, useMemo, type ReactElement, type ReactNode } from 'react';
import { useColorScheme } from 'react-native';

export type RiskTokens = {
  readonly foreground: string;
  readonly background: string;
  readonly border: string;
  readonly icon: string;
};
export type Theme = {
  readonly mode: 'light' | 'dark';
  readonly colors: {
    readonly primary: string;
    readonly background: string;
    readonly surface: string;
    readonly border: string;
    readonly text: string;
    readonly secondaryText: string;
    readonly inverseText: string;
    readonly favorable: RiskTokens;
    readonly caution: RiskTokens;
    readonly flagged: RiskTokens;
    readonly unknown: RiskTokens;
  };
  readonly spacing: {
    readonly xs: 4;
    readonly sm: 8;
    readonly md: 16;
    readonly lg: 24;
    readonly xl: 32;
  };
  readonly radius: { readonly sm: 10; readonly md: 16; readonly lg: 24; readonly pill: 999 };
  readonly type: {
    readonly body: 16;
    readonly caption: 13;
    readonly title: 24;
    readonly score: 28;
    readonly bodyLineHeight: 24;
    readonly captionLineHeight: 18;
    readonly titleLineHeight: 32;
    readonly scoreLineHeight: 36;
    readonly weight: { readonly regular: '400'; readonly medium: '600'; readonly bold: '700' };
  };
  readonly iconSize: { readonly sm: 16; readonly md: 20; readonly lg: 28 };
  readonly minimumTouchTarget: 44;
  readonly elevation: { readonly card: 2; readonly raised: 4 };
};
const light: Theme = {
  mode: 'light',
  colors: {
    primary: '#2457D6',
    background: '#F5F7FC',
    surface: '#FFFFFF',
    border: '#D8DFEC',
    text: '#17233B',
    secondaryText: '#52627D',
    inverseText: '#FFFFFF',
    favorable: { foreground: '#17613B', background: '#E5F4EA', border: '#A9D7B7', icon: '✓' },
    caution: { foreground: '#754600', background: '#FFF1D6', border: '#EACB8A', icon: '−' },
    flagged: { foreground: '#922D28', background: '#FCE9E7', border: '#E7AAA5', icon: '▲' },
    unknown: { foreground: '#394A67', background: '#E9EDF4', border: '#C2CAD8', icon: '?' },
  },
  spacing: { xs: 4, sm: 8, md: 16, lg: 24, xl: 32 },
  radius: { sm: 10, md: 16, lg: 24, pill: 999 },
  type: {
    body: 16,
    bodyLineHeight: 24,
    caption: 13,
    captionLineHeight: 18,
    title: 24,
    titleLineHeight: 32,
    score: 28,
    scoreLineHeight: 36,
    weight: { regular: '400', medium: '600', bold: '700' },
  },
  iconSize: { sm: 16, md: 20, lg: 28 },
  minimumTouchTarget: 44,
  elevation: { card: 2, raised: 4 },
};
const dark: Theme = {
  ...light,
  mode: 'dark',
  colors: {
    primary: '#91AEFF',
    background: '#101827',
    surface: '#1A2638',
    border: '#36445A',
    text: '#F3F6FC',
    secondaryText: '#C1CCDE',
    inverseText: '#101827',
    favorable: { foreground: '#A9E4BC', background: '#193B2B', border: '#3A7952', icon: '✓' },
    caution: { foreground: '#FFDA91', background: '#493517', border: '#92703B', icon: '−' },
    flagged: { foreground: '#FFB4AC', background: '#4A2527', border: '#955255', icon: '▲' },
    unknown: { foreground: '#D4DCEE', background: '#2B374A', border: '#59677E', icon: '?' },
  },
};
const Context = createContext<Theme>(light);
export function ThemeProvider({ children }: { readonly children: ReactNode }): ReactElement {
  const scheme = useColorScheme();
  const value = useMemo(() => (scheme === 'dark' ? dark : light), [scheme]);
  return <Context.Provider value={value}>{children}</Context.Provider>;
}
export function useTheme(): Theme {
  return useContext(Context);
}
export const themeTokens = { light, dark } as const;
