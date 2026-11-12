import React, { useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { useFocusEffect, useNavigation } from '@react-navigation/native';
import { useTranslation } from 'react-i18next';

import { Menu, TopBar } from '../components/AppChrome';
import { Flourish, Icon } from '../components/Icon';
import { AppText, Card, Row, Screen, SectionTitle, Tag, money, useDirection } from '../components/ui';
import { useApp } from '../contexts/AppContext';
import { STYLIST_LINKS } from '../navigation/audience';
import { colors, fonts, gradients, radius, shadows, spacing } from '../theme';
import { useLoad } from './useLoad';

/** A stylist's home: what is coming up and her tools. No customer shopping or assessments. */
export function StylistHomeScreen() {
  const { t, i18n } = useTranslation();
  const { api, user, features, language } = useApp();
  const { rtl } = useDirection();
  const navigation = useNavigation<any>();
  const [menu, setMenu] = useState(false);
  const on = new Set(features ?? []);
  const bookings = useLoad(() => api.practiceBookings().catch(() => []), [api, language]);
  useFocusEffect(React.useCallback(() => { bookings.reload(); }, [bookings.reload])); // eslint-disable-line react-hooks/exhaustive-deps
  const upcoming = (bookings.data ?? []).filter(b => b.status === 'confirmed').sort((a, b) => a.starts_at.localeCompare(b.starts_at));
  const links = STYLIST_LINKS.filter(l => on.has(l.feature));
  const when = (iso: string) => new Date(iso).toLocaleString(i18n.language === 'ar' ? 'ar-AE' : 'en-AE',
    { weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });

  return (
    <Screen testID="stylist-home">
      <ScrollView contentContainerStyle={styles.content}>
        <TopBar onMenu={() => setMenu(true)} />
        <View style={[styles.hero, { backgroundImage: gradients.dusk, boxShadow: shadows.lifted }]}>
          <Flourish />
          <Text style={styles.kicker}>{t('stylistHome.kicker')}</Text>
          <Text style={styles.title}>{t('home.greeting', { name: user?.full_name?.split(' ')[0] ?? '' })}</Text>
          <Text style={styles.note}>{upcoming.length ? t('stylistHome.upcoming', { count: upcoming.length }) : t('stylistHome.none')}</Text>
        </View>

        <Row style={styles.grid}>
          {links.map(l => (
            <Pressable key={l.key} accessibilityRole="button" accessibilityLabel={t(`stylistHome.links.${l.key}`)} testID={`stylist-${l.key}`}
              onPress={() => navigation.navigate(l.screen, l.params)}
              style={({ pressed }) => [styles.tile, { boxShadow: shadows.soft, backgroundImage: gradients.card }, pressed && styles.pressed]}>
              <Row style={styles.tileTop}>
                <View style={styles.bubble}><Icon name={l.icon} color={colors.primary} /></View>
                <View style={styles.flex} />
                <Icon name={rtl ? 'arrow-up-left' : 'arrow-up-right'} size={18} color={colors.gold} />
              </Row>
              <AppText style={styles.label}>{t(`stylistHome.links.${l.key}`)}</AppText>
            </Pressable>
          ))}
        </Row>

        {upcoming.length ? <SectionTitle>{t('stylistHome.next')}</SectionTitle> : null}
        {upcoming.slice(0, 5).map(b => (
          <Card key={b.id}>
            <Row style={styles.row}>
              <View style={styles.flex}>
                <AppText style={styles.bold}>{b.service.title}</AppText>
                <AppText variant="small" muted>{when(b.starts_at)}</AppText>
              </View>
              <Tag label={money(b.price_minor, b.currency)} tone="gold" />
            </Row>
          </Card>
        ))}
      </ScrollView>
      <Menu visible={menu} onClose={() => setMenu(false)} />
    </Screen>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  bold: { fontWeight: '700' },
  content: { padding: spacing.lg, paddingTop: spacing.sm, gap: spacing.lg, paddingBottom: 130 },
  hero: { borderRadius: radius.xl, padding: spacing.lg, gap: 6, overflow: 'hidden', minHeight: 160, justifyContent: 'flex-end' },
  kicker: { color: 'rgba(255,255,255,0.85)', fontSize: 12, letterSpacing: 2, textTransform: 'uppercase', fontWeight: '700' },
  title: { color: colors.onPrimary, fontFamily: fonts.display, fontSize: 30, fontWeight: '700' },
  note: { color: 'rgba(255,255,255,0.92)' },
  grid: { gap: 12, flexWrap: 'wrap' },
  tile: { width: '47%', flexGrow: 1, minHeight: 120, borderRadius: radius.lg, padding: spacing.md, gap: spacing.sm, backgroundColor: colors.surface,
    borderWidth: 1, borderColor: 'rgba(239, 226, 226, 0.7)', justifyContent: 'space-between' },
  pressed: { transform: [{ scale: 0.97 }] },
  tileTop: { alignItems: 'flex-start' },
  bubble: { width: 44, height: 44, borderRadius: 14, backgroundColor: colors.primarySoft, alignItems: 'center', justifyContent: 'center' },
  label: { fontWeight: '700', fontSize: 15 },
  row: { gap: spacing.sm, alignItems: 'center' },
});
