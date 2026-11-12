import React, { useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { useTranslation } from 'react-i18next';

import { Menu, TopBar } from '../components/AppChrome';
import { EntryIcon, Flourish, Icon } from '../components/Icon';
import { AppText, Avatar, LanguageSwitch, Row, Screen, useDirection } from '../components/ui';
import { useApp } from '../contexts/AppContext';
import { visibleSections } from '../navigation/registry';
import { colors, fonts, gradients, radius, shadows, spacing } from '../theme';

/** The "Me" tab: profile card, membership and rewards, language, settings, sign out. */
export function AccountScreen() {
  const { t } = useTranslation();
  const { user, features, signOut } = useApp();
  const { rtl } = useDirection();
  const navigation = useNavigation<any>();
  const [menu, setMenu] = useState(false);
  const entries = visibleSections(features ?? []).find(s => s.group === 'account')?.entries ?? [];
  const items = [
    ...entries.map(e => ({ id: e.id, label: t(`entries.${e.id}`), go: () => e.target && navigation.navigate(e.target.screen, e.target.params) })),
    { id: 'settings', label: t('home.settings'), go: () => navigation.navigate('Settings') },
  ];
  return (
    <Screen testID="account">
      <ScrollView contentContainerStyle={styles.content}>
        <TopBar onMenu={() => setMenu(true)} />
        <View style={[styles.card, { backgroundImage: gradients.hero, boxShadow: shadows.lifted }]}>
          <Flourish />
          <Avatar name={user?.full_name ?? '?'} size={76} />
          <Text style={styles.name}>{user?.full_name}</Text>
          <Text style={styles.email}>{user?.email}</Text>
        </View>
        <View style={[styles.list, { boxShadow: shadows.soft }]}>
          {items.map((item, i) => (
            <Pressable key={item.id} accessibilityRole="button" testID={`me-${item.id}`} onPress={item.go}
              style={({ pressed }) => [styles.item, i > 0 && styles.itemBorder, pressed && styles.pressed]}>
              <Row style={styles.row}>
                <View style={styles.bubble}>
                  {item.id === 'settings' ? <Icon name="settings" size={19} color={colors.primary} /> : <EntryIcon id={item.id} size={19} color={colors.primary} />}
                </View>
                <AppText style={styles.flex}>{item.label}</AppText>
                <Text style={styles.chev}>{rtl ? '‹' : '›'}</Text>
              </Row>
            </Pressable>
          ))}
        </View>
        <LanguageSwitch />
        <Pressable accessibilityRole="button" onPress={signOut} testID="me-sign-out" style={styles.signOut}>
          <Text style={styles.signOutText}>{t('auth.signOut')}</Text>
        </Pressable>
      </ScrollView>
      <Menu visible={menu} onClose={() => setMenu(false)} />
    </Screen>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  content: { padding: spacing.lg, paddingTop: spacing.sm, gap: spacing.lg, paddingBottom: 130 },
  card: { borderRadius: radius.xl, padding: spacing.lg, alignItems: 'center', gap: spacing.xs, overflow: 'hidden' },
  orb: { position: 'absolute', width: 240, height: 240, borderRadius: 120, backgroundColor: 'rgba(255,255,255,0.12)', top: -110, left: -60 },
  name: { color: colors.onPrimary, fontFamily: fonts.display, fontSize: 26, fontWeight: '700', marginTop: spacing.sm },
  email: { color: 'rgba(255,255,255,0.85)' },
  list: { backgroundColor: colors.surface, borderRadius: radius.lg, overflow: 'hidden' },
  item: { paddingHorizontal: spacing.md, paddingVertical: 14 },
  itemBorder: { borderTopWidth: 1, borderTopColor: colors.border },
  pressed: { backgroundColor: colors.primarySoft },
  row: { gap: spacing.md, alignItems: 'center' },
  bubble: { width: 38, height: 38, borderRadius: 12, backgroundColor: colors.primarySoft, alignItems: 'center', justifyContent: 'center' },
  icon: { fontSize: 18 },
  chev: { fontSize: 24, color: colors.muted },
  signOut: { alignSelf: 'center', padding: spacing.sm },
  signOutText: { color: colors.primary, fontWeight: '700', fontSize: 16 },
});
