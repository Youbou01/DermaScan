import AsyncStorage from "@react-native-async-storage/async-storage";
import { getLocales } from "expo-localization";
import i18n from "i18next";
import { initReactI18next } from "react-i18next";

import en from "./en.json";
import fr from "./fr.json";

const STORAGE_KEY = "app.language";
const SUPPORTED = ["en", "fr"] as const;
type Language = (typeof SUPPORTED)[number];

const deviceLanguage = getLocales()[0]?.languageCode ?? "en";

void i18n.use(initReactI18next).init({
  resources: { en: { translation: en }, fr: { translation: fr } },
  lng: SUPPORTED.includes(deviceLanguage as Language) ? deviceLanguage : "en",
  fallbackLng: "en",
  interpolation: { escapeValue: false },
});

// Restore the user's manual choice, if any.
void AsyncStorage.getItem(STORAGE_KEY).then((saved) => {
  if (saved && SUPPORTED.includes(saved as Language)) void i18n.changeLanguage(saved);
});

export async function setLanguage(lang: Language): Promise<void> {
  await AsyncStorage.setItem(STORAGE_KEY, lang);
  await i18n.changeLanguage(lang);
}

export default i18n;
