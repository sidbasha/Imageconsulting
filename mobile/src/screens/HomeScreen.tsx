import React, { useCallback, useState } from 'react';
import { ActivityIndicator, Pressable, RefreshControl, ScrollView, StyleSheet, Text, View } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { useTranslation } from 'react-i18next';

import { AppText, Button, ErrorBanner, Row, Screen } from '../components/ui';
import { useApp } from '../contexts/AppContext';
import { visibleSections, type Entry, type Target } from '../navigation/registry';
import type { AppStackParams } from '../navigation/RootNavigator';
import { colors, gradients, radius, shadows, spacing } from '../theme';
import { errorMessage } from './errorMessage';

export function HomeScreen({ navigation }: NativeStackScreenProps<AppStackParams, 'Home'>) {
  const { t } = useTranslation();
  const { user, features, featuresError, refreshFeatures } = useApp();
  const [refreshing, setRefreshing] = useState(false);

  const refresh = useCallback(async () => {
    setRefreshing(true);
    await refreshFeatures();
    setRefreshing(false);
  }, [refreshFeatures]);

  const sections = features ? visibleSections(features) : [];

  return (
    <Screen testID="home">
      <ScrollView
        contentContainerStyle={styles.content}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={refresh} tintColor={colors.primary} />}>
        <View style={[styles.hero, { backgroundImage: gradients.hero, boxShadow: shadows.lifted }]}>
          <View style={styles.orbLarge} />
          <View style={styles.orbSmall} />
          <Row style={styles.top}>
            <View style={styles.flex}>
              <AppText variant="small" style={styles.heroKicker}>
                {t('home.subtitle')}
              </AppText>
              <AppText variant="title" accessibilityRole="header" style={styles.heroTitle}>
                {t('home.greeting', { name: user?.full_name ?? '' })}
              </AppText>
            </View>
            <Pressable accessibilityRole="button" accessibilityLabel={t('home.settings')} onPress={() => navigation.navigate('Settings')}
              testID="open-settings" style={({ pressed }) => [styles.settings, pressed && styles.pressed]}>
              <Text style={styles.settingsIcon}>⚙︎</Text>
            </Pressable>
          </Row>
          <View style={styles.heroLine} />
          <AppText style={styles.heroNote}>{t('home.tagline')}</AppText>
        </View>

        {featuresError ? (
          <View style={styles.gap}>
            <ErrorBanner message={errorMessage(featuresError, t)} />
            <Button label={t('common.retry')} onPress={refresh} testID="retry-features" />
          </View>
        ) : null}

        {features === null && !featuresError ? (
          <ActivityIndicator color={colors.primary} accessibilityLabel={t('common.loading')} />
        ) : null}

        {features !== null && sections.length === 0 ? <AppText muted>{t('home.empty')}</AppText> : null}

        {sections.map(section => (
          <View key={section.group} style={styles.gap} testID={`group-${section.group}`}>
            <Row style={styles.sectionHead}>
              <View style={[styles.sectionMark, { backgroundImage: gradients.gold }]} />
              <AppText variant="heading" accessibilityRole="header" style={styles.sectionTitle}>
                {t(`groups.${section.group}`)}
              </AppText>
            </Row>
            <Row style={styles.grid}>
              {section.entries.map(entry => (
                <EntryCard key={entry.id} entry={entry} onOpen={target => navigation.navigate(target.screen as any, target.params as any)} />
              ))}
            </Row>
          </View>
        ))}
      </ScrollView>
    </Screen>
  );
}

// A small symbol per service, on a pastel bubble chosen by its group.
const ICONS: Record<string, string> = {
  onboardingQuiz: '✨', styleAssessment: '👗', photoAssessment: '📸', faceShape: '🪞', bodyShape: '💃', seasonalColor: '🎨',
  outfits: '👠', tryOn: '🛍️', outfitColour: '🌈', hair: '💇‍♀️', hairStyles: '💇‍♀️', hairColour: '🎀', eyewear: '🕶️',
  shopping: '🛒', makeupPreview: '💄', findStylist: '👩‍🎨', bookings: '📅', consultations: '💬', messages: '💌',
  occasionAudit: '🥂', wardrobeAudit: '🧥', makeupAudit: '💋', expertColor: '🌸', personalShopper: '👜', nearbyStylists: '📍',
  guides: '📖', reports: '📜', shop: '🎁', offers: '🏷️', vouchers: '🎟️', profile: '🌷', subscription: '👑',
  rewards: '💎', redeem: '🎀', becomeStylist: '🪄',
};
const BUBBLES: Record<string, string> = {
  assessment: colors.primarySoft, recommendations: colors.lilac, experts: colors.peach,
  library: colors.goldSoft, shop: colors.sage, account: colors.primarySoft,
};

function EntryCard({ entry, onOpen }: { entry: Entry; onOpen: (target: Target) => void }) {
  const { t } = useTranslation();
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
          <Text style={styles.icon}>{ICONS[entry.id] ?? '✦'}</Text>
        </View>
      </Row>
      <AppText style={styles.cardLabel} numberOfLines={2}>
        {label}
      </AppText>
      {ready ? null : (
        <View style={styles.badge}>
          <AppText variant="small" muted>
            {t('common.inDevelopment')}
          </AppText>
        </View>
      )}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  content: { padding: spacing.lg, paddingTop: spacing.md, gap: spacing.lg, paddingBottom: spacing.xl * 2 },
  hero: { borderRadius: radius.xl, padding: spacing.lg, gap: spacing.sm, overflow: 'hidden' },
  orbLarge: { position: 'absolute', width: 220, height: 220, borderRadius: 110, backgroundColor: 'rgba(255,255,255,0.12)', top: -70, right: -60 },
  orbSmall: { position: 'absolute', width: 120, height: 120, borderRadius: 60, backgroundColor: 'rgba(255,255,255,0.10)', bottom: -40, left: -30 },
  top: { gap: spacing.md, alignItems: 'flex-start' },
  heroKicker: { color: 'rgba(255,255,255,0.85)', letterSpacing: 1.6, textTransform: 'uppercase', fontWeight: '600' },
  heroTitle: { color: colors.onPrimary, fontSize: 32, lineHeight: 40, marginTop: spacing.xs },
  heroLine: { width: 44, height: 2, borderRadius: 1, backgroundColor: 'rgba(255,255,255,0.7)', marginTop: spacing.xs },
  heroNote: { color: 'rgba(255,255,255,0.92)' },
  settings: { width: 42, height: 42, borderRadius: 21, backgroundColor: 'rgba(255,255,255,0.22)', alignItems: 'center', justifyContent: 'center' },
  settingsIcon: { fontSize: 20, color: colors.onPrimary },
  pressed: { transform: [{ scale: 0.97 }], opacity: 0.94 },
  gap: { gap: spacing.md },
  sectionHead: { gap: spacing.sm, alignItems: 'center' },
  sectionMark: { width: 6, height: 22, borderRadius: 3 },
  sectionTitle: { fontSize: 19, letterSpacing: 0.2 },
  grid: { gap: spacing.md - 4, flexWrap: 'wrap' },
  card: {
    width: '48%',
    flexGrow: 1,
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: 'rgba(239, 226, 226, 0.7)',
    padding: spacing.md,
    minHeight: 124,
    gap: spacing.sm + 2,
  },
  cardRow: { gap: spacing.sm },
  bubble: { width: 46, height: 46, borderRadius: 16, alignItems: 'center', justifyContent: 'center' },
  icon: { fontSize: 22 },
  cardLabel: { fontWeight: '600', fontSize: 15, lineHeight: 20 },
  badge: { backgroundColor: colors.badge, borderRadius: 999, paddingHorizontal: spacing.sm, paddingVertical: 2, alignSelf: 'flex-start' },
});
