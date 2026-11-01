import type { ReactElement } from 'react';
import { fireEvent, render } from '@testing-library/react-native';
import i18n from '@/i18n/i18n';
import type { CategoryNode } from '@/api/types';
import { FilterSheet } from './FilterSheet';
import { clearAll } from './filter-state';

const categories: CategoryNode[] = [
  { slug: 'face-care', name: 'Face care', children: [{ slug: 'serum', name: 'Serum' }] },
];

function setup(onApply: jest.Mock = jest.fn()): { onApply: jest.Mock; element: ReactElement } {
  return {
    onApply,
    element: (
      <FilterSheet
        categories={categories}
        filters={clearAll()}
        onApply={onApply}
        onClose={jest.fn()}
        visible
      />
    ),
  };
}

describe('FilterSheet', () => {
  it('applies the chosen band and category', async () => {
    const { element, onApply } = setup();
    const screen = await render(element);
    await fireEvent.press(screen.getByText(i18n.t('risk.low')));
    await fireEvent.press(screen.getByText(i18n.t('categories.serum')));
    await fireEvent.press(screen.getByText(i18n.t('filters.apply')));
    expect(onApply).toHaveBeenCalledWith({
      category: 'serum',
      bands: ['low'],
      include: [],
      exclude: [],
    });
  });

  it('shows the insufficient data band as an option', async () => {
    const { element } = setup();
    const screen = await render(element);
    expect(screen.getByText(i18n.t('risk.unknown'))).toBeTruthy();
  });

  it('clear all applies empty filters', async () => {
    const { element, onApply } = setup();
    const screen = await render(element);
    await fireEvent.press(screen.getByText(i18n.t('risk.high')));
    await fireEvent.press(screen.getByText(i18n.t('common.clear_all')));
    expect(onApply).toHaveBeenCalledWith(clearAll());
  });

  it('refuses a minimum score above the maximum', async () => {
    const { element, onApply } = setup();
    const screen = await render(element);
    await fireEvent.changeText(screen.getByLabelText(i18n.t('filters.min_score')), '90');
    await fireEvent.changeText(screen.getByLabelText(i18n.t('filters.max_score')), '10');
    expect(screen.getByText(i18n.t('filters.score_range_invalid'))).toBeTruthy();
    await fireEvent.press(screen.getByText(i18n.t('filters.apply')));
    expect(onApply).not.toHaveBeenCalled();
  });
});
