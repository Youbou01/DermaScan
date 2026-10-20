import AsyncStorage from '@react-native-async-storage/async-storage';
import { I18nManager } from 'react-native';
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import type { ReactElement, ReactNode } from 'react';
import { setApiLocale } from '@/api/locale';
import {
  detectDeviceLanguage,
  getActiveLanguage,
  setActiveLanguage,
  type Language,
} from './language-state';
import i18n, { initializeI18n } from './i18n';

const LANGUAGE_KEY = 'preferred-language';

interface LanguageContextValue {
  currentLanguage: Language;
  setLanguage: (language: Language) => Promise<void>;
  isRTL: boolean;
}

const LanguageContext = createContext<LanguageContextValue | null>(null);

export function LanguageProvider({ children }: { children: ReactNode }): ReactElement | null {
  const [currentLanguage, updateCurrentLanguage] = useState<Language>(getActiveLanguage());
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let mounted = true;
    async function initialize(): Promise<void> {
      const deviceLanguage = detectDeviceLanguage();
      let selectedLanguage = deviceLanguage;
      try {
        const savedLanguage = await AsyncStorage.getItem(LANGUAGE_KEY);
        if (savedLanguage === 'en' || savedLanguage === 'fr') selectedLanguage = savedLanguage;
      } catch {
        // A storage failure should leave the app on the detected device language.
      }
      await initializeI18n(selectedLanguage);
      setActiveLanguage(selectedLanguage);
      setApiLocale(selectedLanguage);
      if (mounted) {
        updateCurrentLanguage(selectedLanguage);
        setReady(true);
      }
    }
    void initialize();
    return () => {
      mounted = false;
    };
  }, []);

  const setLanguage = useCallback(async (language: Language): Promise<void> => {
    setActiveLanguage(language);
    setApiLocale(language);
    updateCurrentLanguage(language);
    await i18n.changeLanguage(language);
    try {
      await AsyncStorage.setItem(LANGUAGE_KEY, language);
    } catch {
      // The active session still changes even when persistence is unavailable.
    }
  }, []);

  const value = useMemo(
    () => ({ currentLanguage, setLanguage, isRTL: I18nManager.isRTL }),
    [currentLanguage, setLanguage],
  );

  if (!ready) return null;
  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}

export function useLanguage(): LanguageContextValue {
  const context = useContext(LanguageContext);
  if (!context) throw new Error('useLanguage must be used within LanguageProvider');
  return context;
}
