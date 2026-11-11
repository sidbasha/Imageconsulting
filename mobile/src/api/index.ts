import { API_BASE_URL } from '../config';
import i18n from '../localization';
import { tokenStore } from '../storage/secureStore';
import { createApiClient, type Language } from './client';

export const api = createApiClient({
  baseUrl: API_BASE_URL,
  tokenStore,
  getLanguage: () => i18n.language as Language,
});
