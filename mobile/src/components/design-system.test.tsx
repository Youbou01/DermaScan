import { fireEvent, render } from '@testing-library/react-native';
import { Text } from 'react-native';
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

const riskCases: [RiskLevel, string, string][] = [
  ['low', 'Low concern', '○'],
  ['moderate', 'Moderate concern', '△'],
  ['high', 'High concern', '⬟'],
  ['unknown', 'Insufficient data', '◇'],
];
const product = {
  id: 'product-1',
  name: 'Daily cream',
  brand: 'Example',
  image_url: null,
  score: 80,
  score_band: 'low' as const,
  category_slug: 'moisturizers',
};

describe('RiskBadge', () => {
  it.each(riskCases)(
    'renders %s with icon, text and full accessibility label',
    async (level, label, icon) => {
      const screen = await render(<RiskBadge level={level} />);
      expect(screen.getByText(label)).toBeTruthy();
      expect(screen.getByLabelText(`Risk icon: ${icon}`)).toBeTruthy();
      expect(screen.getByLabelText(`Risk level: ${label}`)).toBeTruthy();
    },
  );
});

describe('ScoreBadge and ProductCard', () => {
  it('announces the numeric score and maximum', async () => {
    expect(
      (await render(<ScoreBadge score={82} band="low" />)).getByLabelText('Score: 82 out of 100'),
    ).toBeTruthy();
  });

  it('renders product details and sends product ID on press', async () => {
    const onPress = jest.fn();
    const screen = await render(<ProductCard product={product} onPress={onPress} />);
    expect(screen.getByText('Daily cream')).toBeTruthy();
    expect(screen.getByText('Example')).toBeTruthy();
    expect(screen.getByLabelText('Score: 80 out of 100')).toBeTruthy();
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
      (await render(<ErrorState onRetry={onRetry} />)).getByRole('button', { name: 'Try again' }),
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
    expect(screen.getByLabelText('Loading')).toHaveStyle({
      width: 128,
      height: 42,
      borderRadius: 6,
    });
  });
});
