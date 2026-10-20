import AsyncStorage from '@react-native-async-storage/async-storage';
import { fireEvent, render, waitFor } from '@testing-library/react-native';
import { Pressable, Text } from 'react-native';
import i18n from './i18n';
import { LanguageProvider, useLanguage } from './LanguageProvider';

function LanguageProbe(): React.ReactElement {
  const { currentLanguage, setLanguage } = useLanguage();
  return (
    <>
      <Text testID="current-language">{currentLanguage}</Text>
      <Pressable accessibilityRole="button" onPress={() => void setLanguage('fr')}>
        <Text>{i18n.t('common.french')}</Text>
      </Pressable>
    </>
  );
}

describe('LanguageProvider', () => {
  beforeEach(async () => {
    await AsyncStorage.clear();
    jest.clearAllMocks();
  });

  it('changes language immediately and persists the manual selection', async () => {
    const screen = await render(
      <LanguageProvider>
        <LanguageProbe />
      </LanguageProvider>,
    );
    await waitFor(() => expect(screen.getByTestId('current-language').props.children).toBe('en'));
    await fireEvent.press(screen.getByRole('button', { name: 'French' }));
    await waitFor(() => expect(screen.getByTestId('current-language').props.children).toBe('fr'));
    expect(i18n.language).toBe('fr');
    expect(await AsyncStorage.getItem('preferred-language')).toBe('fr');
  });

  it('restores a saved preference during initialization', async () => {
    await AsyncStorage.setItem('preferred-language', 'fr');
    const screen = await render(
      <LanguageProvider>
        <LanguageProbe />
      </LanguageProvider>,
    );
    await waitFor(() => expect(screen.getByTestId('current-language').props.children).toBe('fr'));
    expect(i18n.language).toBe('fr');
  });
});
