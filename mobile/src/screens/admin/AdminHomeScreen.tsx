import React, { useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { useFocusEffect, useNavigation } from '@react-navigation/native';
import { useTranslation } from 'react-i18next';

import { Menu, TopBar } from '../../components/AppChrome';
import { Flourish, Icon, type IconName } from '../../components/Icon';
import { AppText, Row, Screen, useDirection } from '../../components/ui';
import { useApp } from '../../contexts/AppContext';
import { colors, fonts, gradients, radius, shadows, spacing } from '../../theme';
import { ADMIN_SECTIONS } from './common';

/** The Admin tab: every staff area this user's role allows, with what is waiting. */
export function AdminHomeScreen() {
  const { t } = useTranslation();
  const { api, user } = useApp();
  const { rtl } = useDirection();
  const navigation = useNavigation<any>();
  const [menu, setMenu] = useState(false);
  const [counts, setCounts] = useState<Record<string, number>>({});
  const mine = ADMIN_SECTIONS.filter(s => (user?.permissions ?? []).includes(s.permission));

  useFocusEffect(
    React.useCallback(() => {
      let live = true;
      (async () => {
        const next: Record<string, number> = {};
        for (const s of mine) {
          const paths = [('count' in s && s.count) || null, ('count2' in s && s.count2) || null].filter(Boolean) as string[];
          let total = 0;
          for (const path of paths) {
            total += ((await api.call<unknown[]>('GET', path).catch(() => [])) ?? []).length;
          }
          next[s.key] = total;
        }
        if (live) {
          setCounts(next);
        }
      })();
      return () => {
        live = false;
      };
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [api, user]),
  );
  const waiting = Object.values(counts).reduce((a, b) => a + b, 0);

  return (
    <Screen testID="admin-home">
      <ScrollView contentContainerStyle={styles.content}>
        <TopBar onMenu={() => setMenu(true)} />
        <View style={[styles.hero, { backgroundImage: gradients.plum, boxShadow: shadows.lifted }]}>
          <Flourish />
          <Text style={styles.kicker}>{t('admin.kicker')}</Text>
          <Text style={styles.title}>{t('admin.title')}</Text>
          <Text style={styles.note}>{waiting ? t('admin.waiting', { count: waiting }) : t('admin.allClear')}</Text>
        </View>
        <Row style={styles.grid}>
          {mine.map(s => (
            <Pressable key={s.key} accessibilityRole="button" accessibilityLabel={t(`admin.sections.${s.key}`)} testID={`admin-${s.key}`}
              onPress={() => navigation.navigate(s.screen)}
              style={({ pressed }) => [styles.tile, { boxShadow: shadows.soft, backgroundImage: gradients.card }, pressed && styles.pressed]}>
              <Row style={styles.tileTop}>
                <View style={styles.bubble}>
                  <Icon name={s.icon as IconName} color={colors.primary} />
                </View>
                <View style={styles.flex} />
                {counts[s.key] ? (
                  <View style={[styles.badge, { backgroundImage: gradients.primary }]}>
                    <Text style={styles.badgeText}>{counts[s.key]}</Text>
                  </View>
                ) : (
                  <Icon name={rtl ? 'arrow-up-left' : 'arrow-up-right'} size={18} color={colors.gold} />
                )}
              </Row>
              <AppText style={styles.label}>{t(`admin.sections.${s.key}`)}</AppText>
              <AppText variant="small" muted numberOfLines={2}>{t(`admin.hints.${s.key}`)}</AppText>
            </Pressable>
          ))}
        </Row>
      </ScrollView>
      <Menu visible={menu} onClose={() => setMenu(false)} />
    </Screen>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  content: { padding: spacing.lg, paddingTop: spacing.sm, gap: spacing.lg, paddingBottom: 130 },
  hero: { borderRadius: radius.xl, padding: spacing.lg, gap: 6, overflow: 'hidden', minHeight: 150, justifyContent: 'flex-end' },
  kicker: { color: 'rgba(255,255,255,0.85)', fontSize: 12, letterSpacing: 2, textTransform: 'uppercase', fontWeight: '700' },
  title: { color: colors.onPrimary, fontFamily: fonts.display, fontSize: 30, fontWeight: '700' },
  note: { color: 'rgba(255,255,255,0.92)' },
  grid: { gap: 12, flexWrap: 'wrap' },
  tile: { width: '47%', flexGrow: 1, borderRadius: radius.lg, padding: spacing.md, gap: 6, backgroundColor: colors.surface,
    borderWidth: 1, borderColor: 'rgba(239, 226, 226, 0.7)', minHeight: 140 },
  pressed: { transform: [{ scale: 0.97 }] },
  tileTop: { alignItems: 'flex-start', marginBottom: 4 },
  bubble: { width: 44, height: 44, borderRadius: 14, backgroundColor: colors.primarySoft, alignItems: 'center', justifyContent: 'center' },
  badge: { minWidth: 26, height: 26, borderRadius: 13, paddingHorizontal: 8, alignItems: 'center', justifyContent: 'center' },
  badgeText: { color: colors.onPrimary, fontWeight: '700', fontSize: 13 },
  label: { fontWeight: '700', fontSize: 15 },
});
