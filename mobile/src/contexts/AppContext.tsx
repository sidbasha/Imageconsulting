import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { AppState } from 'react-native';

import { api as defaultApi } from '../api';
import { ApiError, type ApiClient, type Language, type User } from '../api/client';
import i18n, { isRTL } from '../localization';
import { loadChosenLanguage, saveChosenLanguage } from '../storage/secureStore';

type Status = 'starting' | 'unreachable' | 'signedOut' | 'signedIn';

type AppState_ = {
  status: Status;
  user: User | null;
  language: Language;
  rtl: boolean;
  /** Feature keys enabled in the active release; null until first loaded. */
  features: string[] | null;
  featuresError: ApiError | null;
  /** One-off message for the sign-in screen, e.g. after the session expired. */
  notice: 'sessionExpired' | null;
  signIn(email: string, password: string): Promise<void>;
  register(input: { email: string; password: string; fullName: string }): Promise<void>;
  signOut(): Promise<void>;
  setLanguage(language: Language): Promise<void>;
  refreshFeatures(): Promise<void>;
  retryStart(): void;
};

const Context = createContext<AppState_ | null>(null);

export function useApp(): AppState_ {
  const value = useContext(Context);
  if (!value) {
    throw new Error('useApp must be used inside <AppProvider>');
  }
  return value;
}

const asApiError = (error: unknown) =>
  error instanceof ApiError ? error : new ApiError(0, 'unexpected_error', String(error));

export function AppProvider({ children, api = defaultApi }: { children: React.ReactNode; api?: ApiClient }) {
  const [status, setStatus] = useState<Status>('starting');
  const [user, setUser] = useState<User | null>(null);
  const [language, setLanguageState] = useState<Language>(i18n.language as Language);
  const [features, setFeatures] = useState<string[] | null>(null);
  const [featuresError, setFeaturesError] = useState<ApiError | null>(null);
  const [notice, setNotice] = useState<AppState_['notice']>(null);
  const [attempt, setAttempt] = useState(0);
  const signedIn = useRef(false);

  useEffect(() => {
    const handler = (next: string) => setLanguageState(next as Language);
    i18n.on('languageChanged', handler);
    return () => i18n.off('languageChanged', handler);
  }, []);

  const refreshFeatures = useCallback(async () => {
    try {
      const enabled = await api.enabledFeatures();
      setFeatures(enabled.features);
      setFeaturesError(null);
    } catch (error) {
      // Keep the last known list on screen; the server still enforces access.
      setFeaturesError(asApiError(error));
    }
  }, [api]);

  /**
   * One language everywhere. A language picked on this device wins and is
   * saved to the profile; with no local pick, the profile's language is used.
   */
  const adoptLanguage = useCallback(
    async (profile: User): Promise<User> => {
      const chosen = await loadChosenLanguage();
      if (chosen && chosen !== profile.preferred_language) {
        return api.updateMe({ preferred_language: chosen }).catch(() => profile);
      }
      if (!chosen && profile.preferred_language !== i18n.language) {
        await i18n.changeLanguage(profile.preferred_language);
      }
      return profile;
    },
    [api],
  );

  const enter = useCallback(
    async (profile: User) => {
      const current = await adoptLanguage(profile);
      signedIn.current = true;
      setUser(current);
      setNotice(null);
      setStatus('signedIn');
      await refreshFeatures();
    },
    [adoptLanguage, refreshFeatures],
  );

  const leave = useCallback((reason: AppState_['notice']) => {
    signedIn.current = false;
    setUser(null);
    setFeatures(null);
    setFeaturesError(null);
    setNotice(reason);
    setStatus('signedOut');
  }, []);

  // Start-up: restore language, then the session.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      const chosen = await loadChosenLanguage();
      if (chosen && chosen !== i18n.language) {
        await i18n.changeLanguage(chosen);
      }
      try {
        const profile = await api.restoreSession();
        if (cancelled) {
          return;
        }
        if (profile) {
          await enter(profile);
        } else {
          setStatus('signedOut');
        }
      } catch (error) {
        if (cancelled) {
          return;
        }
        // Offline is not "signed out": keep the tokens and offer a retry.
        if (asApiError(error).code === 'network_error') {
          setStatus('unreachable');
        } else if (!signedIn.current) {
          setStatus('signedOut');
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [api, enter, attempt]);

  useEffect(() => api.onSessionExpired(() => leave('sessionExpired')), [api, leave]);

  // A phase released while the app was in the background shows up on return.
  useEffect(() => {
    const subscription = AppState.addEventListener('change', next => {
      if (next === 'active' && signedIn.current) {
        refreshFeatures();
      }
    });
    return () => subscription.remove();
  }, [refreshFeatures]);

  const value = useMemo<AppState_>(
    () => ({
      status,
      user,
      language,
      rtl: isRTL(language),
      features,
      featuresError,
      notice,
      signIn: async (email, password) => enter(await api.login(email, password)),
      register: async ({ email, password, fullName }) =>
        enter(await api.register({ email, password, full_name: fullName, preferred_language: i18n.language as Language })),
      signOut: async () => {
        await api.logout();
        leave(null);
      },
      setLanguage: async next => {
        await i18n.changeLanguage(next); // screens re-render in the new language and direction at once
        await saveChosenLanguage(next);
        if (signedIn.current) {
          const updated = await api.updateMe({ preferred_language: next }).catch(() => null);
          if (updated) {
            setUser(updated);
          }
        }
      },
      refreshFeatures,
      retryStart: () => {
        setStatus('starting');
        setAttempt(n => n + 1);
      },
    }),
    [status, user, language, features, featuresError, notice, api, enter, leave, refreshFeatures],
  );

  return <Context.Provider value={value}>{children}</Context.Provider>;
}
