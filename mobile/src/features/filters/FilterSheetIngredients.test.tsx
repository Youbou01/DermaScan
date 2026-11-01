import { fireEvent, render } from '@testing-library/react-native';
import i18n from '@/i18n/i18n';
import { FilterSheet } from './FilterSheet';
import { clearAll } from './filter-state';

describe('FilterSheet ingredients', () => {
  it('applies an included ingredient', async () => {
    const onApply = jest.fn();
    const screen = await render(
      <FilterSheet
        categories={[]}
        filters={clearAll()}
        onApply={onApply}
        onClose={jest.fn()}
        visible
      />,
    );
    await fireEvent.changeText(screen.getByLabelText(i18n.t('filters.include_title')), 'aq');
    await fireEvent.press(screen.getByText('Aqua'));
    await fireEvent.press(screen.getByText(i18n.t('filters.apply')));
    expect(onApply).toHaveBeenCalledWith({ bands: [], include: ['Aqua'], exclude: [] });
  });
});
