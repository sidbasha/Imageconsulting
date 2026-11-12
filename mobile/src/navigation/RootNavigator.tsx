import React from 'react';
import { ActivityIndicator, StyleSheet, View } from 'react-native';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { useTranslation } from 'react-i18next';

import { AppText, Button, Screen } from '../components/ui';
import type { RecommendationCategory } from '../api/client';
import { useApp } from '../contexts/AppContext';
import { AssessmentScreen } from '../screens/AssessmentScreen';
import { PhotosScreen } from '../screens/PhotosScreen';
import { RecommendationsScreen } from '../screens/RecommendationsScreen';
import { LoginScreen, RegisterScreen } from '../screens/AuthScreens';
import { HomeScreen } from '../screens/HomeScreen';
import { SettingsScreen } from '../screens/SettingsScreen';
import { colors, spacing } from '../theme';

export type AuthStackParams = { Login: undefined; Register: undefined };
export type AppStackParams = {
  Home: undefined;
  Settings: undefined;
  Assessment: { key: string };
  Recommendations: { category: RecommendationCategory };
  Photos: undefined;
};

const AuthStack = createNativeStackNavigator<AuthStackParams>();
const AppStack = createNativeStackNavigator<AppStackParams>();

// Screens draw their own headers so that direction follows the chosen language.
const screenOptions = { headerShown: false, contentStyle: { backgroundColor: colors.background } };

export function RootNavigator() {
  const { status, retryStart, rtl } = useApp();
  const { t } = useTranslation();

  if (status === 'starting') {
    return (
      <Screen testID="starting">
        <View style={styles.center}>
          <ActivityIndicator size="large" color={colors.primary} accessibilityLabel={t('common.loading')} />
        </View>
      </Screen>
    );
  }
  if (status === 'unreachable') {
    return (
      <Screen testID="unreachable">
        <View style={styles.center}>
          <AppText style={styles.centerText}>{t('errors.network_error')}</AppText>
          <Button label={t('common.retry')} onPress={retryStart} testID="retry-start" />
        </View>
      </Screen>
    );
  }
  const animation = rtl ? 'slide_from_left' : 'slide_from_right';
  return (
    <NavigationContainer>
      {status === 'signedIn' ? (
        <AppStack.Navigator screenOptions={{ ...screenOptions, animation }}>
          <AppStack.Screen name="Home" component={HomeScreen} />
          <AppStack.Screen name="Settings" component={SettingsScreen} />
          <AppStack.Screen name="Assessment" component={AssessmentScreen} />
          <AppStack.Screen name="Recommendations" component={RecommendationsScreen} />
          <AppStack.Screen name="Photos" component={PhotosScreen} />
        </AppStack.Navigator>
      ) : (
        <AuthStack.Navigator screenOptions={{ ...screenOptions, animation }}>
          <AuthStack.Screen name="Login" component={LoginScreen} />
          <AuthStack.Screen name="Register" component={RegisterScreen} />
        </AuthStack.Navigator>
      )}
    </NavigationContainer>
  );
}

const styles = StyleSheet.create({
  center: { flex: 1, alignItems: 'stretch', justifyContent: 'center', padding: spacing.lg, gap: spacing.lg },
  centerText: { textAlign: 'center' },
});
