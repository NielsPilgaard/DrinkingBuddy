import * as SecureStore from 'expo-secure-store';

export type Language = 'da' | 'en';
export type DrinkType = 'alcoholic' | 'non_alcoholic';

export type Filters = {
  language: Language;
  drink_type: DrinkType;
  location: string;
};

export const LANGUAGES: { value: Language; label: string }[] = [
  { value: 'da', label: 'Dansk' },
  { value: 'en', label: 'English' },
];

export const DRINK_TYPES: { value: DrinkType; label: string }[] = [
  { value: 'alcoholic', label: 'Alcoholic' },
  { value: 'non_alcoholic', label: 'Non-alcoholic' },
];

// Denmark-only at MVP (PRD §3), so location is fixed rather than picked.
export const DEFAULT_FILTERS: Filters = {
  language: 'da',
  drink_type: 'alcoholic',
  location: 'dk',
};

const FILTERS_KEY = 'match_filters';

export async function getStoredFilters(): Promise<Filters> {
  const raw = await SecureStore.getItemAsync(FILTERS_KEY);
  if (!raw) return DEFAULT_FILTERS;
  try {
    const parsed = JSON.parse(raw);
    const language = LANGUAGES.find((l) => l.value === parsed?.language)?.value;
    const drinkType = DRINK_TYPES.find((d) => d.value === parsed?.drink_type)?.value;
    return {
      ...DEFAULT_FILTERS,
      language: language ?? DEFAULT_FILTERS.language,
      drink_type: drinkType ?? DEFAULT_FILTERS.drink_type,
    };
  } catch {
    return DEFAULT_FILTERS;
  }
}

export async function setStoredFilters(filters: Filters): Promise<void> {
  await SecureStore.setItemAsync(FILTERS_KEY, JSON.stringify(filters));
}
