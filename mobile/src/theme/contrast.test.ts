import { contrastRatio } from './contrast';
import { themeTokens } from './theme';
describe('theme text contrast', () => {
  it('meets WCAG AA for all semantic label pairs', () => {
    for (const theme of Object.values(themeTokens)) {
      for (const key of ['favorable', 'caution', 'flagged', 'unknown'] as const)
        expect(
          contrastRatio(theme.colors[key].foreground, theme.colors[key].background),
        ).toBeGreaterThanOrEqual(4.5);
      expect(contrastRatio(theme.colors.text, theme.colors.background)).toBeGreaterThanOrEqual(4.5);
      expect(
        contrastRatio(theme.colors.secondaryText, theme.colors.background),
      ).toBeGreaterThanOrEqual(4.5);
    }
  });
});
