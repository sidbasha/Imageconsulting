import React from 'react';
import { StatusBar } from 'react-native';
import { SafeAreaProvider } from 'react-native-safe-area-context';

import type { ApiClient } from './src/api/client';
import { AppProvider } from './src/contexts/AppContext';
import './src/localization';
import { RootNavigator } from './src/navigation/RootNavigator';

/** `api` is injectable so tests can run the whole app against a fake server. */
export default function App({ api }: { api?: ApiClient }) {
  return (
    <SafeAreaProvider>
      <StatusBar barStyle="dark-content" />
      <AppProvider api={api}>
        <RootNavigator />
      </AppProvider>
    </SafeAreaProvider>
  );
}
