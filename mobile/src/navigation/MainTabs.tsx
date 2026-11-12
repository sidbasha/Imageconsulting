/**
 * Bottom navigation: a floating, frosted pill. Tabs appear only when the
 * active release has something in them, so Phase 1 shows Home, Style and Me.
 */
import React from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { createBottomTabNavigator, type BottomTabBarProps } from '@react-navigation/bottom-tabs';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useTranslation } from 'react-i18next';

import { Icon, type IconName } from '../components/Icon';
import { useDirection } from '../components/ui';
import { useApp } from '../contexts/AppContext';
import { AccountScreen } from '../screens/AccountScreen';
import { AdminHomeScreen } from '../screens/admin/AdminHomeScreen';
import { StylistHomeScreen } from '../screens/StylistHomeScreen';
import { audienceOf } from './audience';
import { HomeScreen } from '../screens/HomeScreen';
import { HubScreen } from '../screens/HubScreen';
import { colors, gradients, radius, shadows, spacing } from '../theme';
import { visibleSections, type Group } from './registry';

export type TabParams = { Today: undefined; Style: undefined; Experts: undefined; Shop: undefined; Admin: undefined; Me: undefined };

const Tab = createBottomTabNavigator<TabParams>();
const TAB_GROUPS: Record<'Style' | 'Experts' | 'Shop', Group[]> = {
  Style: ['assessment', 'recommendations'],
  Experts: ['experts'],
  Shop: ['library', 'shop'],
};
const ICONS: Record<keyof TabParams, IconName> = { Today: 'house', Style: 'sparkles', Experts: 'flower', Shop: 'bag', Admin: 'shield', Me: 'user' };

const StyleHub = () => <HubScreen tab="Style" groups={TAB_GROUPS.Style} />;
const ExpertsHub = () => <HubScreen tab="Experts" groups={TAB_GROUPS.Experts} />;
const ShopHub = () => <HubScreen tab="Shop" groups={TAB_GROUPS.Shop} />;

const renderTabBar = (props: BottomTabBarProps) => <FloatingTabBar {...props} />;

export function MainTabs() {
  const { features, user } = useApp();
  const audience = audienceOf(user);
  const groups = new Set(visibleSections(features ?? []).map(s => s.group));
  const has = (tab: keyof typeof TAB_GROUPS) => TAB_GROUPS[tab].some(g => groups.has(g));
  if (audience === 'staff') {
    // Staff work in the Admin workspace; customer screens are not theirs.
    return (
      <Tab.Navigator screenOptions={{ headerShown: false }} tabBar={renderTabBar}>
        <Tab.Screen name="Admin" component={AdminHomeScreen} />
        <Tab.Screen name="Me" component={AccountScreen} />
      </Tab.Navigator>
    );
  }
  if (audience === 'stylist') {
    return (
      <Tab.Navigator screenOptions={{ headerShown: false }} tabBar={renderTabBar}>
        <Tab.Screen name="Today" component={StylistHomeScreen} />
        <Tab.Screen name="Me" component={AccountScreen} />
      </Tab.Navigator>
    );
  }
  return (
    <Tab.Navigator screenOptions={{ headerShown: false }} tabBar={renderTabBar}>
      <Tab.Screen name="Today" component={HomeScreen} />
      {has('Style') ? <Tab.Screen name="Style" component={StyleHub} /> : null}
      {has('Experts') ? <Tab.Screen name="Experts" component={ExpertsHub} /> : null}
      {has('Shop') ? <Tab.Screen name="Shop" component={ShopHub} /> : null}
      <Tab.Screen name="Me" component={AccountScreen} />
    </Tab.Navigator>
  );
}

function FloatingTabBar({ state, navigation }: BottomTabBarProps) {
  const { t } = useTranslation();
  const insets = useSafeAreaInsets();
  const { row } = useDirection();
  return (
    <View pointerEvents="box-none" style={[styles.wrap, { paddingBottom: Math.max(insets.bottom, spacing.md) }]}>
      <View style={[styles.bar, { flexDirection: row, boxShadow: shadows.lifted }]}>
        {state.routes.map((route, index) => {
          const focused = state.index === index;
          const name = route.name as keyof TabParams;
          return (
            <Pressable key={route.key} accessibilityRole="tab" accessibilityState={{ selected: focused }}
              accessibilityLabel={t(`tabs.${name}`)} testID={`tab-${name}`}
              onPress={() => {
                const event = navigation.emit({ type: 'tabPress', target: route.key, canPreventDefault: true });
                if (!focused && !event.defaultPrevented) {
                  navigation.navigate(route.name);
                }
              }}
              style={[styles.item, focused && [styles.itemOn, { backgroundImage: gradients.primary }]]}>
              <Icon name={ICONS[name]} size={21} color={focused ? colors.onPrimary : colors.muted} strokeWidth={focused ? 2 : 1.6} />
              {focused ? <Text style={styles.label} numberOfLines={1}>{t(`tabs.${name}`)}</Text> : null}
            </Pressable>
          );
        })}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { position: 'absolute', left: 0, right: 0, bottom: 0, paddingHorizontal: spacing.md },
  bar: { backgroundColor: 'rgba(255, 255, 255, 0.94)', borderRadius: radius.pill, padding: 6, alignItems: 'center',
    justifyContent: 'space-between', borderWidth: 1, borderColor: 'rgba(239, 226, 226, 0.9)' },
  item: { height: 48, minWidth: 48, borderRadius: radius.pill, alignItems: 'center', justifyContent: 'center', flexDirection: 'row', gap: 6, paddingHorizontal: 12 },
  itemOn: { paddingHorizontal: 16 },
  label: { color: colors.onPrimary, fontWeight: '700', fontSize: 13 },
});
