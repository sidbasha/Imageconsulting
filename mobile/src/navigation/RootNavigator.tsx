import React from 'react';
import { ActivityIndicator, StyleSheet, View } from 'react-native';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { useTranslation } from 'react-i18next';

import { AppText, Button, Screen } from '../components/ui';
import type { AnalysisKind, PreviewKind, RecommendationCategory, TryOnKind } from '../api/client';
import { useApp } from '../contexts/AppContext';
import { AssessmentScreen } from '../screens/AssessmentScreen';
import { PhotosScreen } from '../screens/PhotosScreen';
import { TryOnScreen } from '../screens/TryOnScreen';
import { StylistServicesScreen } from '../screens/StylistServicesScreen';
import { ReportEditorScreen } from '../screens/ReportEditorScreen';
import { WorkspaceScreen } from '../screens/WorkspaceScreen';
import { FeaturedScreen } from '../screens/FeaturedScreen';
import { PhotoAnalysisScreen } from '../screens/PhotoAnalysisScreen';
import { PreviewScreen } from '../screens/PreviewScreen';
import { LibraryScreen } from '../screens/LibraryScreen';
import { PlansScreen } from '../screens/PlansScreen';
import { RetailScreen } from '../screens/RetailScreen';
import { RewardsScreen } from '../screens/RewardsScreen';
import { ProfileScreen } from '../screens/ProfileScreen';
import { ShopScreen } from '../screens/ShopScreen';
import { OffersScreen } from '../screens/OffersScreen';
import { StylistsScreen } from '../screens/StylistsScreen';
import { StylistScreen } from '../screens/StylistScreen';
import { BookingsScreen } from '../screens/BookingsScreen';
import { ConsultationScreen } from '../screens/ConsultationScreen';
import { MessagesScreen, ThreadScreen } from '../screens/MessagesScreen';
import { StylistApplicationScreen } from '../screens/StylistApplicationScreen';
import { PracticeScreen } from '../screens/PracticeScreen';
import { RecommendationsScreen } from '../screens/RecommendationsScreen';
import { LoginScreen, RegisterScreen } from '../screens/AuthScreens';
import { MainTabs } from './MainTabs';
import { SettingsScreen } from '../screens/SettingsScreen';
import { colors, spacing } from '../theme';

export type AuthStackParams = { Login: undefined; Register: undefined };
export type AppStackParams = {
  Home: undefined;
  Settings: undefined;
  Assessment: { key: string };
  Recommendations: { category: RecommendationCategory };
  Photos: undefined;
  PhotoAnalysis: { kind: AnalysisKind };
  Preview: { kind: PreviewKind };
  Library: { kind?: 'guide' | 'report' | 'workspace_credits' } | undefined;
  Plans: { audience?: 'customer' | 'consultant' } | undefined;
  Retail: undefined;
  Rewards: undefined;
  Profile: undefined;
  Shop: undefined;
  Offers: { show?: 'offers' | 'vouchers' } | undefined;
  Stylists: { kind?: string } | undefined;
  Stylist: { id: string };
  Bookings: undefined;
  Consultation: { id: string };
  Messages: undefined;
  Thread: { id: string; name: string };
  StylistApplication: undefined;
  Practice: undefined;
  TryOn: { kind: TryOnKind };
  StylistServices: undefined;
  ReportEditor: { id: string };
  Workspace: { id: string };
  Featured: undefined;
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
          <AppStack.Screen name="Home" component={MainTabs} />
          <AppStack.Screen name="Settings" component={SettingsScreen} />
          <AppStack.Screen name="Assessment" component={AssessmentScreen} />
          <AppStack.Screen name="Recommendations" component={RecommendationsScreen} />
          <AppStack.Screen name="Photos" component={PhotosScreen} />
          <AppStack.Screen name="PhotoAnalysis" component={PhotoAnalysisScreen} />
          <AppStack.Screen name="Preview" component={PreviewScreen} />
          <AppStack.Screen name="Library" component={LibraryScreen} />
          <AppStack.Screen name="Plans" component={PlansScreen} />
          <AppStack.Screen name="Retail" component={RetailScreen} />
          <AppStack.Screen name="Rewards" component={RewardsScreen} />
          <AppStack.Screen name="Profile" component={ProfileScreen} />
          <AppStack.Screen name="Shop" component={ShopScreen} />
          <AppStack.Screen name="Offers" component={OffersScreen} />
          <AppStack.Screen name="Stylists" component={StylistsScreen} />
          <AppStack.Screen name="Stylist" component={StylistScreen} />
          <AppStack.Screen name="Bookings" component={BookingsScreen} />
          <AppStack.Screen name="Consultation" component={ConsultationScreen} />
          <AppStack.Screen name="Messages" component={MessagesScreen} />
          <AppStack.Screen name="Thread" component={ThreadScreen} />
          <AppStack.Screen name="StylistApplication" component={StylistApplicationScreen} />
          <AppStack.Screen name="Practice" component={PracticeScreen} />
          <AppStack.Screen name="TryOn" component={TryOnScreen} />
          <AppStack.Screen name="StylistServices" component={StylistServicesScreen} />
          <AppStack.Screen name="ReportEditor" component={ReportEditorScreen} />
          <AppStack.Screen name="Workspace" component={WorkspaceScreen} />
          <AppStack.Screen name="Featured" component={FeaturedScreen} />
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
