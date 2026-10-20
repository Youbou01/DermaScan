import { render, screen } from '@testing-library/react-native';
import { I18nProvider } from '@/i18n';
import { ThemeProvider } from '@/theme/theme';
import { RiskBadge } from './index';
async function renderBadge(level: 'low' | 'moderate' | 'high' | 'unknown'): Promise<void> {
  await render(
    <ThemeProvider>
      <I18nProvider>
        <RiskBadge level={level} />
      </I18nProvider>
    </ThemeProvider>,
  );
}
describe('RiskBadge', () => {
  it.each([
    ['low', 'Low concern', '✓'],
    ['moderate', 'Moderate concern', '−'],
    ['high', 'High concern', '▲'],
    ['unknown', 'Not enough data', '?'],
  ] as const)('announces icon and label for %s', async (level, label, icon) => {
    await renderBadge(level);
    expect(screen.getByText(label)).toBeTruthy();
    expect(screen.getByText(icon)).toBeTruthy();
    expect(screen.getByLabelText(label)).toBeTruthy();
  });
});
