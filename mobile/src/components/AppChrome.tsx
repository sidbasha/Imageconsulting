/**
 * App chrome shared by the tab screens: the top bar (menu, wordmark, avatar)
 * and the slide-in menu listing every service in the active release.
 */
import React, { useEffect, useRef } from 'react';
import { Animated, Dimensions, Modal, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useTranslation } from 'react-i18next';

import { useApp } from '../contexts/AppContext';
import { audienceOf, STYLIST_LINKS } from '../navigation/audience';
import { visibleSections } from '../navigation/registry';
import { ADMIN_SECTIONS } from '../screens/admin/common';
import { colors, fonts, gradients, radius, shadows, spacing } from '../theme';
import { AppText, Avatar, LanguageSwitch, Row, useDirection } from './ui';
import { EntryIcon, Icon, type IconName } from './Icon';

export function TopBar({ onMenu }: { onMenu: () => void }) {
  const { t } = useTranslation();
  const { user } = useApp();
  const navigation = useNavigation<any>();
  return (
    <Row style={styles.bar}>
      <Pressable accessibilityRole="button" accessibilityLabel={t('menu.open')} onPress={onMenu} testID="open-menu"
        style={({ pressed }) => [styles.roundButton, { boxShadow: shadows.soft }, pressed && styles.pressed]}>
        <View style={styles.burger}>
          <View style={[styles.burgerLine, styles.burgerLong]} />
          <View style={[styles.burgerLine, styles.burgerShort]} />
          <View style={[styles.burgerLine, styles.burgerLong]} />
        </View>
      </Pressable>
      <View style={styles.wordmark}>
        <Text style={styles.wordmarkText}>{t('auth.brand')}</Text>
        <View style={[styles.wordmarkLine, { backgroundImage: gradients.gold }]} />
      </View>
      <Pressable accessibilityRole="button" accessibilityLabel={t('home.settings')} onPress={() => navigation.navigate('Settings')}
        testID="open-settings" style={({ pressed }) => [pressed && styles.pressed]}>
        <Avatar name={user?.full_name ?? '?'} size={42} />
      </Pressable>
    </Row>
  );
}

export function Menu({ visible, onClose }: { visible: boolean; onClose: () => void }) {
  const { t } = useTranslation();
  const { user, features, signOut } = useApp();
  const { rtl } = useDirection();
  const insets = useSafeAreaInsets();
  const navigation = useNavigation<any>();
  const width = Math.min(Dimensions.get('window').width * 0.84, 360);
  const slide = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.timing(slide, { toValue: visible ? 1 : 0, duration: 260, useNativeDriver: true }).start();
  }, [slide, visible]);

  const offset = slide.interpolate({ inputRange: [0, 1], outputRange: [rtl ? width : -width, 0] });
  const open = (target: { screen: string; params?: object }) => {
    onClose();
    navigation.navigate(target.screen, target.params);
  };
  // What this person may open: customer services, a stylist's tools, or the staff areas of her role.
  const audience = audienceOf(user);
  const on = new Set(features ?? []);
  type Item = { id: string; label: string; icon: React.ReactNode; target: { screen: string; params?: object } };
  const menuGroups: { title: string; items: Item[] }[] =
    audience === 'staff'
      ? [{ title: t('tabs.Admin'), items: ADMIN_SECTIONS.filter(a => (user?.permissions ?? []).includes(a.permission)).map(a => ({
          id: a.key, label: t(`admin.sections.${a.key}`), icon: <Icon name={a.icon as IconName} size={20} color={colors.primary} />, target: { screen: a.screen } })) }]
      : audience === 'stylist'
        ? [{ title: t('stylistHome.kicker'), items: STYLIST_LINKS.filter(l => on.has(l.feature)).map(l => ({
            id: l.key, label: t(`stylistHome.links.${l.key}`), icon: <Icon name={l.icon} size={20} color={colors.primary} />, target: { screen: l.screen, params: l.params } })) }]
        : visibleSections(features ?? []).map(section => ({
            title: t(`groups.${section.group}`),
            items: section.entries.filter(e => e.target).map(e => ({
              id: e.id, label: t(`entries.${e.id}`), icon: <EntryIcon id={e.id} size={20} color={colors.primary} />, target: e.target! })),
          }));

  return (
    <Modal visible={visible} transparent animationType="fade" onRequestClose={onClose} statusBarTranslucent>
      <Pressable style={styles.backdrop} onPress={onClose} accessibilityLabel={t('menu.close')} testID="close-menu" />
      <Animated.View style={[styles.panel, { width, paddingTop: insets.top + spacing.md, transform: [{ translateX: offset }] },
        rtl ? styles.panelRight : styles.panelLeft]}>
        <View style={[styles.panelHead, { backgroundImage: gradients.hero }]}>
          <Avatar name={user?.full_name ?? '?'} size={58} />
          <View style={styles.flex}>
            <Text style={styles.panelName}>{user?.full_name}</Text>
            <Text style={styles.panelEmail}>{user?.email}</Text>
          </View>
        </View>
        <ScrollView contentContainerStyle={styles.panelList}>
          {menuGroups.map(group => (
            <View key={group.title} style={styles.panelGroup}>
              <Text style={styles.panelGroupTitle}>{group.title}</Text>
              {group.items.map(item => (
                <Pressable key={item.id} accessibilityRole="button" testID={`menu-${item.id}`} onPress={() => open(item.target)}
                  style={({ pressed }) => [styles.panelItem, pressed && styles.panelItemPressed]}>
                  <Row style={styles.panelItemRow}>
                    <View style={styles.panelIcon}>{item.icon}</View>
                    <AppText style={styles.flex}>{item.label}</AppText>
                  </Row>
                </Pressable>
              ))}
            </View>
          ))}
          <View style={styles.panelFoot}>
            <LanguageSwitch />
            <Pressable accessibilityRole="button" onPress={() => { onClose(); signOut(); }} testID="menu-sign-out" style={styles.signOut}>
              <Text style={styles.signOutText}>{t('auth.signOut')}</Text>
            </Pressable>
          </View>
        </ScrollView>
      </Animated.View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  bar: { alignItems: 'center', justifyContent: 'space-between', gap: spacing.md },
  roundButton: { width: 44, height: 44, borderRadius: 22, backgroundColor: colors.surface, alignItems: 'center', justifyContent: 'center' },
  pressed: { transform: [{ scale: 0.95 }], opacity: 0.9 },
  burger: { gap: 4, alignItems: 'flex-start' },
  burgerLine: { height: 2, borderRadius: 1, backgroundColor: colors.primaryDeep },
  burgerLong: { width: 18 },
  burgerShort: { width: 12 },
  wordmark: { alignItems: 'center', gap: 3 },
  wordmarkText: { fontFamily: fonts.display, fontSize: 19, color: colors.primaryDeep, letterSpacing: 1.5 },
  wordmarkLine: { width: 24, height: 2, borderRadius: 1 },
  backdrop: { ...StyleSheet.absoluteFill, backgroundColor: 'rgba(46, 31, 39, 0.38)' },
  panel: { position: 'absolute', top: 0, bottom: 0, backgroundColor: colors.background, boxShadow: '0px 0px 40px rgba(46,31,39,0.25)' },
  panelLeft: { left: 0, borderTopRightRadius: radius.xl, borderBottomRightRadius: radius.xl },
  panelRight: { right: 0, borderTopLeftRadius: radius.xl, borderBottomLeftRadius: radius.xl },
  panelHead: { marginHorizontal: spacing.md, borderRadius: radius.lg, padding: spacing.md, flexDirection: 'row', alignItems: 'center', gap: spacing.md },
  panelName: { color: colors.onPrimary, fontSize: 18, fontWeight: '700' },
  panelEmail: { color: 'rgba(255,255,255,0.85)', fontSize: 13 },
  panelList: { padding: spacing.md, gap: spacing.md, paddingBottom: spacing.xl * 2 },
  panelGroup: { gap: 2 },
  panelGroupTitle: { fontSize: 12, fontWeight: '700', color: colors.gold, letterSpacing: 1.4, textTransform: 'uppercase', marginBottom: 4, marginHorizontal: spacing.sm },
  panelItem: { borderRadius: radius.md, paddingVertical: 10, paddingHorizontal: spacing.sm },
  panelItemPressed: { backgroundColor: colors.primarySoft },
  panelItemRow: { gap: spacing.md, alignItems: 'center' },
  panelIcon: { width: 36, height: 36, borderRadius: 12, backgroundColor: colors.primarySoft, alignItems: 'center', justifyContent: 'center' },
  panelFoot: { gap: spacing.md, marginTop: spacing.sm },
  signOut: { paddingVertical: spacing.sm },
  signOutText: { color: colors.primary, fontWeight: '700', fontSize: 16 },
});
