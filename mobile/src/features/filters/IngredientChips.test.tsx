import { fireEvent, render } from '@testing-library/react-native';
import i18n from '@/i18n/i18n';
import { IngredientChips } from './IngredientChips';

const title = 'Must contain';

describe('IngredientChips', () => {
  it('adds a suggested name', async () => {
    const onAdd = jest.fn();
    const screen = await render(
      <IngredientChips names={[]} onAdd={onAdd} onRemove={jest.fn()} title={title} />,
    );
    await fireEvent.changeText(screen.getByLabelText(title), 'aq');
    await fireEvent.press(screen.getByText('Aqua'));
    expect(onAdd).toHaveBeenCalledWith('Aqua');
  });

  it('suggests nothing for an unknown name', async () => {
    const screen = await render(
      <IngredientChips names={[]} onAdd={jest.fn()} onRemove={jest.fn()} title={title} />,
    );
    await fireEvent.changeText(screen.getByLabelText(title), 'zzz');
    expect(screen.queryByText('Aqua')).toBeNull();
  });

  it('ignores case when suggesting', async () => {
    const screen = await render(
      <IngredientChips names={[]} onAdd={jest.fn()} onRemove={jest.fn()} title={title} />,
    );
    await fireEvent.changeText(screen.getByLabelText(title), 'GLYC');
    expect(screen.getByText('Glycerin')).toBeTruthy();
  });

  it('removes a chosen name', async () => {
    const onRemove = jest.fn();
    const screen = await render(
      <IngredientChips names={['Aqua']} onAdd={jest.fn()} onRemove={onRemove} title={title} />,
    );
    await fireEvent.press(screen.getByLabelText(`${i18n.t('filters.remove')} Aqua`));
    expect(onRemove).toHaveBeenCalledWith('Aqua');
  });
});
