import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

import type { Language } from '../api/client';
import ar from './ar/translation.json';
import en from './en/translation.json';

/**
 * To add a language: add a folder next to en/ and ar/, register it here and
 * in RTL_LANGUAGES if it is written right to left. Nothing else changes.
 */
export const LANGUAGES: Language[] = ['en', 'ar'];
const RTL_LANGUAGES: readonly string[] = ['ar'];

export const isRTL = (language: string) => RTL_LANGUAGES.includes(language);

// Arabic copy addresses the user in the feminine form: the client's audience
// decision in the meeting minutes is women. All Arabic needs native review.

i18n.use(initReactI18next).init({
  resources: { en: { translation: en }, ar: { translation: ar } },
  lng: 'en',
  fallbackLng: 'en',
  interpolation: { escapeValue: false },
  returnNull: false,
});

export default i18n;
