import * as Keychain from 'react-native-keychain';

import type { Language, Tokens, TokenStore } from '../api/client';

// iOS Keychain / Android Keystore. Tokens never touch plain storage.
const TOKENS = { service: 'com.imageconsulting.session' };
const LANGUAGE = { service: 'com.imageconsulting.language' };

export const tokenStore: TokenStore = {
  async load() {
    const entry = await Keychain.getGenericPassword(TOKENS);
    if (!entry) {
      return null;
    }
    try {
      return JSON.parse(entry.password) as Tokens;
    } catch {
      return null;
    }
  },
  async save(tokens) {
    await Keychain.setGenericPassword('session', JSON.stringify(tokens), TOKENS);
  },
  async clear() {
    await Keychain.resetGenericPassword(TOKENS);
  },
};

/** The language the person picked on this device, or null if they never picked one. */
export async function loadChosenLanguage(): Promise<Language | null> {
  const entry = await Keychain.getGenericPassword(LANGUAGE);
  return entry && (entry.password === 'en' || entry.password === 'ar') ? entry.password : null;
}

export async function saveChosenLanguage(language: Language): Promise<void> {
  await Keychain.setGenericPassword('language', language, LANGUAGE);
}
