import React, { useCallback, useState } from 'react';
import { ActivityIndicator, Dimensions, Pressable, RefreshControl, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { useTranslation } from 'react-i18next';

import { Menu, TopBar } from '../components/AppChrome';
import { EntryIcon, Flourish, Icon, type IconName } from '../components/Icon';
import { AppText, Avatar, Button, ErrorBanner, Rating, Row, Screen, useDirection } from '../components/ui';
import { useApp } from '../contexts/AppContext';
import { ENTRIES, visibleSections, type Entry, type Group, type Target } from '../navigation/registry';
import { colors, fonts, gradients, radius, shadows, spacing } from '../theme';
import { errorMessage } from './errorMessage';
import { useLoad } from './useLoad';

const CARD_WIDTH = Math.min(Dimensions.get('window').width - spacing.lg * 2 - 28, 340);

// Large feature cards, shown when their feature is in the active release.
const FEATURED: { id: string; feature: string; gradient: string; icon: IconName; target: Target }[] = [
  { id: 'colours', feature: 'phase1.seasonal_color', gradient: gradients.hero, icon: 'palette', target: { screen: 'PhotoAnalysis', params: { kind: 'seasonal_color' } } },
  { id: 'tryOn', feature: 'phase1.virtual_tryon', gradient: gradients.plum, icon: 'shirt', target: { screen: 'TryOn', params: { kind: 'garment' } } },
  { id: 'stylist', feature: 'phase2.stylist_discovery', gradient: gradients.dusk, icon: 'user-search', target: { screen: 'Stylists' } },
  { id: 'style', feature: 'phase1.style_assessment', gradient: gradients.champagne, icon: 'sparkles', target: { screen: 'Assessment', params: { key: 'style' } } },
];
const QUICK = ['photoAssessment', 'hairStyles', 'outfits', 'bookings', 'messages', 'rewards', 'guides'];
const TONES: Record<Group, string> = {
  assessment: '#A23E66', recommendations: '#6F4A8E', experts: '#B5603F', library: '#8A6638', shop: '#2F6B4F', account: '#A23E66',
};
const BUBBLES: Record<Group, string> = {
  assessment: colors.primarySoft, recommendations: colors.lilac, experts: colors.peach,
  library: colors.goldSoft, shop: colors.sage, account: colors.primarySoft,
};

export function HomeScreen() {
  const { t } = useTranslation();
  const { api, user, features, featuresError, refreshFeatures, language } = useApp();
  const navigation = useNavigation<any>();
  const [refreshing, setRefreshing] = useState(false);
  const [menu, setMenu] = useState(false);
  const [query, setQuery] = useState('');
  const on = new Set(features ?? []);
  const progress = useLoad(() => api.assessments().catch(() => null), [api, language, features]);
  const stylistsOn = on.has('phase2.stylist_discovery');
  const stylists = useLoad(() => (stylistsOn ? api.stylists().catch(() => []) : Promise.resolve([])), [api, stylistsOn, language]);

  const refresh = useCallback(async () => {
    setRefreshing(true);
    await refreshFeatures();
    setRefreshing(false);
  }, [refreshFeatures]);

  const open = (target: Target) => navigation.navigate(target.screen, target.params);
  const sections = features ? visibleSections(features) : [];
  const featured = FEATURED.filter(f => on.has(f.feature));
  const quick = QUICK.map(id => ENTRIES.find(e => e.id === id)!).filter(e => e && on.has(e.feature) && e.target);
  const needle = query.trim().toLowerCase();
  const found = needle ? sections.flatMap(s => s.entries).filter(e => t(`entries.${e.id}`).toLowerCase().includes(needle)) : [];

  const scored = (progress.data ?? []).filter(a => a.key !== 'onboarding_quiz');
  const done = scored.filter(a => a.completed_at);
  const next = scored.find(a => !a.completed_at);

  return (
    <Screen testID="home">
      <ScrollView
        contentContainerStyle={styles.content}
        keyboardShouldPersistTaps="handled"
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={refresh} tintColor={colors.primary} />}>
        <TopBar onMenu={() => setMenu(true)} />

        <View style={styles.greeting}>
          <Text style={styles.kicker}>{t('home.kicker')}</Text>
          <AppText variant="title" accessibilityRole="header" style={styles.hello}>
            {t('home.greeting', { name: user?.full_name ?? '' })}
          </AppText>
          <AppText muted>{t('home.tagline')}</AppText>
        </View>

        <View style={[styles.search, { boxShadow: shadows.soft }]}>
          <Icon name="search" size={20} color={colors.primary} />
          <TextInput value={query} onChangeText={setQuery} placeholder={t('home.search')} placeholderTextColor={colors.muted}
            accessibilityLabel={t('home.search')} testID="home-search" style={styles.searchInput} />
        </View>

        {featuresError ? (
          <View style={styles.gap}>
            <ErrorBanner message={errorMessage(featuresError, t)} />
            <Button label={t('common.retry')} onPress={refresh} testID="retry-features" />
          </View>
        ) : null}
        {features === null && !featuresError ? <ActivityIndicator color={colors.primary} accessibilityLabel={t('common.loading')} /> : null}
        {features !== null && sections.length === 0 ? <AppText muted>{t('home.empty')}</AppText> : null}

        {needle ? (
          <View style={styles.gap}>
            {found.length === 0 ? <AppText muted>{t('home.noResults')}</AppText> : null}
            {found.map(entry => (
              <Pressable key={entry.id} accessibilityRole="button" testID={`found-${entry.id}`} onPress={() => entry.target && open(entry.target)}
                style={[styles.found, { boxShadow: shadows.soft }]}>
                <EntryIcon id={entry.id} color={colors.primary} />
                <Text style={styles.foundText}>{t(`entries.${entry.id}`)}</Text>
              </Pressable>
            ))}
          </View>
        ) : (
          <>
            {featured.length ? (
              <ScrollView horizontal showsHorizontalScrollIndicator={false} snapToInterval={CARD_WIDTH + 14} decelerationRate="fast"
                style={styles.bleed} contentContainerStyle={styles.carousel}>
                {featured.map(card => (
                  <Pressable key={card.id} accessibilityRole="button" accessibilityLabel={t(`home.featured.${card.id}.title`)} testID={`featured-${card.id}`}
                    onPress={() => open(card.target)}
                    style={({ pressed }) => [styles.feature, { width: CARD_WIDTH, backgroundImage: card.gradient, boxShadow: shadows.lifted }, pressed && styles.pressed]}>
                    <Flourish />
                    <View style={styles.orbSmall} />
                    <View style={styles.featureText}>
                      <Row style={styles.featureTop}>
                        <View style={styles.featureGlass}>
                          <Icon name={card.icon} size={17} color={colors.onPrimary} strokeWidth={1.6} />
                        </View>
                        <Text style={styles.featureKicker}>{t(`home.featured.${card.id}.kicker`)}</Text>
                      </Row>
                      <Text style={styles.featureTitle}>{t(`home.featured.${card.id}.title`)}</Text>
                      <View style={styles.featureCta}>
                        <Text style={styles.featureCtaText}>{t(`home.featured.${card.id}.cta`)} →</Text>
                      </View>
                    </View>
                  </Pressable>
                ))}
              </ScrollView>
            ) : null}

            {scored.length ? (
              <View style={[styles.profile, { boxShadow: shadows.soft }]} testID="style-profile">
                <Row style={styles.profileHead}>
                  <View style={styles.flex}>
                    <AppText variant="heading">{t('home.profileTitle')}</AppText>
                    <AppText variant="small" muted>{t('home.profileProgress', { done: done.length, total: scored.length })}</AppText>
                  </View>
                  <Text style={styles.percent}>{`${Math.round((done.length / scored.length) * 100)}%`}</Text>
                </Row>
                <Row style={styles.segments}>
                  {scored.map(a => <View key={a.key} style={[styles.segment, a.completed_at ? { backgroundImage: gradients.primary } : null]} />)}
                </Row>
                <Row style={styles.results}>
                  {done.map(a => (
                    <View key={a.key} style={styles.result}>
                      <Text style={styles.resultText}>{a.result}</Text>
                    </View>
                  ))}
                </Row>
                {next ? (
                  <Button kind="soft" label={t('home.profileNext', { title: next.title })} testID="profile-next"
                    onPress={() => navigation.navigate('Assessment', { key: next.key })} />
                ) : null}
              </View>
            ) : null}

            {quick.length ? (
              <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.bleed} contentContainerStyle={styles.quickRow}>
                {quick.map(entry => (
                  <Pressable key={entry.id} accessibilityRole="button" accessibilityLabel={t(`home.quick.${entry.id}`)} testID={`quick-${entry.id}`}
                    onPress={() => entry.target && open(entry.target)} style={({ pressed }) => [styles.quick, pressed && styles.pressed]}>
                    <View style={[styles.quickRing, { backgroundImage: gradients.hero }]}>
                      <View style={styles.quickInner}>
                        <EntryIcon id={entry.id} size={24} color={colors.primary} strokeWidth={1.5} />
                      </View>
                    </View>
                    <Text style={styles.quickLabel} numberOfLines={1}>{t(`home.quick.${entry.id}`)}</Text>
                  </Pressable>
                ))}
              </ScrollView>
            ) : null}

            {stylists.data?.length ? (
              <View style={styles.gap}>
                <SectionHead title={t('home.topStylists')} action={t('home.seeAll')} onAction={() => navigation.navigate('Stylists')} />
                <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.bleed} contentContainerStyle={styles.rowScroll}>
                  {stylists.data.slice(0, 6).map(s => (
                    <Pressable key={s.id} accessibilityRole="button" testID={`top-stylist-${s.id}`} onPress={() => navigation.navigate('Stylist', { id: s.id })}
                      style={({ pressed }) => [styles.stylist, { boxShadow: shadows.soft }, pressed && styles.pressed]}>
                      <Avatar name={s.display_name} size={64} />
                      <Text style={styles.stylistName} numberOfLines={1}>{s.display_name.split(' ')[0]}</Text>
                      {s.city ? <Text style={styles.stylistCity} numberOfLines={1}>{s.city}</Text> : null}
                      <Rating value={s.rating_avg} count={s.rating_count} />
                    </Pressable>
                  ))}
                </ScrollView>
              </View>
            ) : null}

            {sections.map(section => (
              <View key={section.group} style={styles.gap} testID={`group-${section.group}`}>
                <SectionHead title={t(`groups.${section.group}`)} />
                <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.bleed} contentContainerStyle={styles.rowScroll}>
                  {section.entries.map(entry => <EntryCard key={entry.id} entry={entry} onOpen={open} />)}
                </ScrollView>
              </View>
            ))}
          </>
        )}
      </ScrollView>
      <Menu visible={menu} onClose={() => setMenu(false)} />
    </Screen>
  );
}

function SectionHead({ title, action, onAction }: { title: string; action?: string; onAction?: () => void }) {
  return (
    <Row style={styles.sectionHead}>
      <View style={[styles.sectionMark, { backgroundImage: gradients.gold }]} />
      <AppText variant="heading" accessibilityRole="header" style={styles.sectionTitle}>
        {title}
      </AppText>
      {action ? (
        <Pressable accessibilityRole="button" onPress={onAction}>
          <Text style={styles.sectionAction}>{action}</Text>
        </Pressable>
      ) : null}
    </Row>
  );
}

function EntryCard({ entry, onOpen }: { entry: Entry; onOpen: (target: Target) => void }) {
  const { t } = useTranslation();
  const { rtl } = useDirection();
  const ready = !!entry.target;
  const label = t(`entries.${entry.id}`);
  return (
    <Pressable
      testID={`entry-${entry.id}`}
      accessibilityRole="button"
      accessibilityLabel={ready ? label : `${label}, ${t('common.inDevelopment')}`}
      accessibilityState={{ disabled: !ready }}
      disabled={!ready}
      onPress={() => entry.target && onOpen(entry.target)}
      style={({ pressed }) => [styles.card, { boxShadow: shadows.soft, backgroundImage: gradients.card }, pressed && styles.pressed]}>
      <Row style={styles.cardRow}>
        <View style={[styles.bubble, { backgroundColor: BUBBLES[entry.group] }]}>
          <EntryIcon id={entry.id} color={TONES[entry.group]} />
        </View>
        <View style={styles.flex} />
        <Icon name={rtl ? 'arrow-up-left' : 'arrow-up-right'} size={18} color={colors.gold} />
      </Row>
      <AppText style={styles.cardLabel} numberOfLines={2}>
        {label}
      </AppText>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  content: { padding: spacing.lg, paddingTop: spacing.sm, gap: spacing.lg, paddingBottom: 130 },
  bleed: { marginHorizontal: -spacing.lg },
  greeting: { gap: 2 },
  kicker: { fontSize: 12, fontWeight: '700', color: colors.gold, letterSpacing: 2, textTransform: 'uppercase' },
  hello: { fontSize: 34, lineHeight: 42 },
  search: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm, backgroundColor: colors.surface, borderRadius: radius.pill,
    paddingHorizontal: spacing.md, minHeight: 52 },
  searchIcon: { fontSize: 22, color: colors.primary },
  searchInput: { flex: 1, fontSize: 16, color: colors.text, paddingVertical: 0 },
  found: { flexDirection: 'row', alignItems: 'center', gap: spacing.md, backgroundColor: colors.surface, borderRadius: radius.md, padding: spacing.md },
  foundText: { fontSize: 16, color: colors.text, fontWeight: '600' },
  carousel: { gap: 14, paddingHorizontal: spacing.lg, paddingBottom: spacing.md },
  feature: { height: 216, borderRadius: radius.xl, padding: spacing.lg, overflow: 'hidden', justifyContent: 'flex-end' },
  orbLarge: { position: 'absolute', width: 220, height: 220, borderRadius: 110, backgroundColor: 'rgba(255,255,255,0.13)', top: -80, right: -60 },
  orbSmall: { position: 'absolute', width: 110, height: 110, borderRadius: 55, backgroundColor: 'rgba(255,255,255,0.10)', bottom: -40, left: -30 },
  featureTop: { gap: 8, alignItems: 'center' },
  featureGlass: { width: 32, height: 32, borderRadius: 16, alignItems: 'center', justifyContent: 'center',
    backgroundColor: 'rgba(255,255,255,0.2)', borderWidth: 1, borderColor: 'rgba(255,255,255,0.45)' },
  featureText: { gap: 6, alignItems: 'flex-start' },
  featureKicker: { color: 'rgba(255,255,255,0.85)', fontSize: 11, fontWeight: '700', letterSpacing: 1.8, textTransform: 'uppercase' },
  featureTitle: { color: colors.onPrimary, fontFamily: fonts.display, fontSize: 25, lineHeight: 31, fontWeight: '700', maxWidth: '72%' },
  featureCta: { backgroundColor: 'rgba(255,255,255,0.94)', borderRadius: radius.pill, paddingHorizontal: 14, paddingVertical: 7, marginTop: 4 },
  featureCtaText: { color: colors.primaryDeep, fontWeight: '700', fontSize: 13 },
  profile: { backgroundColor: colors.surface, borderRadius: radius.lg, padding: spacing.md + 2, gap: spacing.md },
  profileHead: { alignItems: 'center', gap: spacing.md },
  percent: { fontFamily: fonts.display, fontSize: 30, color: colors.primary, fontWeight: '700' },
  segments: { gap: 6 },
  segment: { flex: 1, height: 7, borderRadius: 4, backgroundColor: colors.primarySoft },
  results: { gap: 6, flexWrap: 'wrap' },
  result: { backgroundColor: colors.goldSoft, borderRadius: radius.pill, paddingHorizontal: 12, paddingVertical: 4 },
  resultText: { color: '#8A6638', fontWeight: '700', fontSize: 12 },
  quickRow: { gap: spacing.md, paddingHorizontal: spacing.lg },
  quick: { alignItems: 'center', gap: 6, width: 68 },
  quickRing: { width: 64, height: 64, borderRadius: 32, alignItems: 'center', justifyContent: 'center' },
  quickInner: { width: 58, height: 58, borderRadius: 29, backgroundColor: colors.surface, alignItems: 'center', justifyContent: 'center' },
  quickIcon: { fontSize: 26 },
  quickLabel: { fontSize: 12, color: colors.text, fontWeight: '600' },
  rowScroll: { gap: 12, paddingHorizontal: spacing.lg, paddingBottom: spacing.md },
  stylist: { width: 128, backgroundColor: colors.surface, borderRadius: radius.lg, padding: spacing.md, alignItems: 'center', gap: 4 },
  stylistName: { fontWeight: '700', color: colors.text, fontSize: 15, marginTop: 4 },
  stylistCity: { color: colors.muted, fontSize: 12 },
  pressed: { transform: [{ scale: 0.97 }], opacity: 0.94 },
  gap: { gap: spacing.md },
  sectionHead: { gap: spacing.sm, alignItems: 'center' },
  sectionMark: { width: 6, height: 22, borderRadius: 3 },
  sectionTitle: { fontSize: 19, letterSpacing: 0.2, flex: 1 },
  sectionAction: { color: colors.primary, fontWeight: '700' },
  card: { width: 148, minHeight: 138, backgroundColor: colors.surface, borderRadius: radius.lg, borderWidth: 1,
    borderColor: 'rgba(239, 226, 226, 0.7)', padding: spacing.md, justifyContent: 'space-between' },
  cardRow: { gap: spacing.sm, alignItems: 'flex-start' },
  bubble: { width: 46, height: 46, borderRadius: 16, alignItems: 'center', justifyContent: 'center' },
  icon: { fontSize: 22 },
  arrow: { color: colors.gold, fontSize: 16, fontWeight: '700' },
  cardLabel: { fontWeight: '600', fontSize: 15, lineHeight: 20 },
});
