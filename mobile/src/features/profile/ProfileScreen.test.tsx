import type { ReactElement } from 'react';
import { fireEvent, render } from '@testing-library/react-native';
import { LanguageProvider } from '@/i18n/LanguageProvider';
import { ProfileScreen } from './ProfileScreen';

const mockMutate = jest.fn();
const mockProfile = {
  user_id: 'test-user',
  skin_type: 'sensitive',
  is_pregnant_or_nursing: false,
  health_conditions: ['eczema'],
  allergy_ingredient_ids: [],
  blacklisted_product_ids: ['0194f024-6c67-7e21-9e16-a774b0d53311'],
};
jest.mock('expo-router', () => ({ useRouter: () => ({ push: jest.fn() }) }));
jest.mock('@/features/auth/AuthProvider', () => ({
  useAuth: () => ({ user: { id: 'test-user' }, isReady: true, isAuthenticated: true }),
}));
jest.mock('@/api/hooks', () => ({
  useProfileQuery: () => ({
    data: mockProfile,
    isPending: false,
    isError: false,
    refetch: jest.fn(),
  }),
  useUpdateProfileMutation: () => ({ mutate: mockMutate, isPending: false, isError: false }),
}));

function renderScreen(): ReactElement {
  return (
    <LanguageProvider>
      <ProfileScreen />
    </LanguageProvider>
  );
}

describe('ProfileScreen', () => {
  beforeEach(() => mockMutate.mockClear());

  it('shows profile values, updates life-stage settings, and removes a blacklisted product', async () => {
    const screen = await render(renderScreen());
    expect(screen.getByRole('radio', { name: 'Sensitive' }).props.accessibilityState.selected).toBe(
      true,
    );
    await fireEvent.press(screen.getByRole('switch', { name: 'Pregnant or nursing' }));
    expect(mockMutate).toHaveBeenCalledWith(
      expect.objectContaining({ is_pregnant_or_nursing: true }),
    );
    await fireEvent.press(screen.getByRole('button', { name: 'Remove Gentle Cream Cleanser' }));
    expect(mockMutate).toHaveBeenLastCalledWith(
      expect.objectContaining({ blacklisted_product_ids: [] }),
    );
  });

  it('requires a valid ingredient UUID for the ID-only allergy contract', async () => {
    const screen = await render(renderScreen());
    await fireEvent.changeText(screen.getByLabelText('Ingredient ID'), 'not-an-id');
    await fireEvent.press(screen.getByRole('button', { name: 'Add ingredient ID' }));
    expect(screen.getByText('Enter a valid ingredient ID.')).toBeTruthy();
    expect(mockMutate).not.toHaveBeenCalled();
  });
});
