import { fireEvent, render } from '@testing-library/react-native';
import { Text } from 'react-native';
import i18n from '@/i18n/i18n';
import type { RiskLevel } from '@/api/types';
import {
  EmptyState,
  ErrorState,
  ProductCard,
  RiskBadge,
  ScoreBadge,
  Screen,
  Skeleton,
} from '@/components';

const riskCases: [RiskLevel, `risk.${RiskLevel}`][] = [
  ['low', 'risk.low'],
  ['moderate', 'risk.moderate'],
  ['high', 'risk.high'],
  ['unknown', 'risk.unknown'],
];
const product = {
  id: 'product-1',
  name: 'Daily cream',
  brand: 'Example',
  image_url: null,
  score: 80,
  score_band: 'low' as const,
  category_slug: 'moisturizer',
};

describe('RiskBadge', () => {
  it.each(riskCases)(
    'renders %s with icon, text and full accessibility label',
    async (level, labelKey) => {
      const screen = await render(<RiskBadge level={level} />);
      const label = i18n.t(labelKey);
      expect(screen.getByText(label)).toBeTruthy();
      expect(screen.getByLabelText(i18n.t(`risk.accessibility.${level}`))).toBeTruthy();
    },
  );
});

describe('ScoreBadge and ProductCard', () => {
  it('announces the numeric score and maximum', async () => {
    expect(
      (await render(<ScoreBadge score={82} band="low" />)).getByLabelText(
        i18n.t('common.score', { value: i18n.t('common.score_out_of', { score: 82 }) }),
      ),
    ).toBeTruthy();
  });

  it('renders product details and sends product ID on press', async () => {
    const onPress = jest.fn();
    const screen = await render(<ProductCard product={product} onPress={onPress} />);
    expect(screen.getByText('Daily cream')).toBeTruthy();
    expect(screen.getByText('Example')).toBeTruthy();
    expect(screen.getByText(i18n.t('categories.moisturizer'))).toBeTruthy();
    expect(
      screen.getByLabelText(
        i18n.t('common.score', { value: i18n.t('common.score_out_of', { score: 80 }) }),
      ),
    ).toBeTruthy();
    await fireEvent.press(screen.getByRole('button', { name: 'Daily cream, Example' }));
    expect(onPress).toHaveBeenCalledWith('product-1');
  });
});

describe('state and loading components', () => {
  it('renders children inside a scrollable safe-area screen', async () => {
    expect(
      (
        await render(
          <Screen>
            <Text>Screen content</Text>
          </Screen>,
        )
      ).getByText('Screen content'),
    ).toBeTruthy();
  });

  it('calls the retry action', async () => {
    const onRetry = jest.fn();
    await fireEvent.press(
      (await render(<ErrorState onRetry={onRetry} />)).getByRole('button', {
        name: i18n.t('common.retry'),
      }),
    );
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it('renders a custom empty state action', async () => {
    const screen = await render(
      <EmptyState
        title="Nothing here"
        description="Try adding an item."
        action={<Text>Add item</Text>}
      />,
    );
    expect(screen.getByText('Add item')).toBeTruthy();
    expect(screen.getByText('Nothing here')).toBeTruthy();
  });

  it('accepts custom dimensions and radius', async () => {
    const screen = await render(
      <Skeleton variant="rect" width={128} height={42} borderRadius={6} />,
    );
    expect(screen.getByLabelText(i18n.t('common.loading'))).toHaveStyle({
      width: 128,
      height: 42,
      borderRadius: 6,
    });
  });
});
