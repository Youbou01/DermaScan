import type { CategoryNode } from '@/api/types';
import en from './en.json';
import fr from './fr.json';
import { getActiveLanguage, type Language } from './language-state';

type LocalizedCategory = keyof typeof en.categories;
const dictionaries = { en, fr } as const;

export function getLocalizedCategory(
  category: Pick<CategoryNode, 'slug' | 'name'>,
  language: Language = getActiveLanguage(),
): string {
  const localizedCategories: Partial<Record<LocalizedCategory, string>> =
    dictionaries[language].categories;
  const localizedName = localizedCategories[category.slug as LocalizedCategory];
  return localizedName?.trim() ? localizedName : category.name;
}

export function getLocalizedCategorySlug(
  slug: string,
  language: Language = getActiveLanguage(),
): string | null {
  const localizedCategories: Partial<Record<LocalizedCategory, string>> =
    dictionaries[language].categories;
  const localizedName = localizedCategories[slug as LocalizedCategory];
  return localizedName?.trim() ? localizedName : null;
}
