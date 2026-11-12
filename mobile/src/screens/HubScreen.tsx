import React, { useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { useTranslation } from 'react-i18next';

import { Menu, TopBar } from '../components/AppChrome';
import { ENTRY_ICONS } from '../components/entryIcons';
import { AppText, Row, Screen } from '../components/ui';
import { useApp } from '../contexts/AppContext';
import { visibleSections, type Group } from '../navigation/registry';
import { colors, gradients, radius, shadows, spacing } from '../theme';

const BUBBLES: Record<Group, string> = {
  assessment: colors.primarySoft, recommendations: colors.lilac, experts: colors.peach,
  library: colors.goldSoft, shop: colors.sage, account: colors.primarySoft,
};

/** A tab listing the services of one or more groups as a bento grid. */
export function HubScreen({ tab, groups }: { tab: string; groups: Group[] }) {
  const { t } = useTranslation();
  const { features } = useApp();
  const navigation = useNavigation<any>();
  const [menu, setMenu] = useState(false);
  const sections = visibleSections(features ?? []).filter(s => groups.includes(s.group));
  return (
    <Screen testID={`hub-${tab}`}>
      <ScrollView contentContainerStyle={styles.content}>
        <TopBar onMenu={() => setMenu(true)} />
        <View style={styles.head}>
          <AppText variant="title">{t(`tabs.${tab}Title`)}</AppText>
          <AppText muted>{t(`tabs.${tab}Intro`)}</AppText>
        </View>
        {sections.map(section => (
          <View key={section.group} style={styles.section}>
            <Text style={styles.kicker}>{t(`groups.${section.group}`)}</Text>
            <Row style={styles.grid}>
              {section.entries.map((entry, i) => {
                const wide = section.entries.length % 2 === 1 && i === 0;
                return (
                  <Pressable key={entry.id} accessibilityRole="button" accessibilityLabel={t(`entries.${entry.id}`)} testID={`hub-entry-${entry.id}`}
                    onPress={() => entry.target && navigation.navigate(entry.target.screen, entry.target.params)}
                    style={({ pressed }) => [styles.tile, wide && styles.tileWide, { boxShadow: shadows.soft, backgroundImage: wide ? gradients.hero : gradients.card },
                      pressed && styles.pressed]}>
                    <View style={[styles.bubble, wide ? styles.bubbleWide : { backgroundColor: BUBBLES[section.group] }]}>
                      <Text style={styles.icon}>{ENTRY_ICONS[entry.id] ?? '✦'}</Text>
                    </View>
                    <AppText style={[styles.label, wide && styles.labelWide]} numberOfLines={2}>{t(`entries.${entry.id}`)}</AppText>
                  </Pressable>
                );
              })}
            </Row>
          </View>
        ))}
      </ScrollView>
      <Menu visible={menu} onClose={() => setMenu(false)} />
    </Screen>
  );
}

const styles = StyleSheet.create({
  content: { padding: spacing.lg, paddingTop: spacing.sm, gap: spacing.lg, paddingBottom: 130 },
  head: { gap: spacing.xs },
  section: { gap: spacing.sm },
  kicker: { fontSize: 12, fontWeight: '700', color: colors.gold, letterSpacing: 1.6, textTransform: 'uppercase' },
  grid: { gap: 12, flexWrap: 'wrap' },
  tile: { width: '47%', flexGrow: 1, minHeight: 128, borderRadius: radius.lg, padding: spacing.md, gap: spacing.sm, backgroundColor: colors.surface,
    borderWidth: 1, borderColor: 'rgba(239, 226, 226, 0.7)', justifyContent: 'space-between' },
  tileWide: { width: '100%', minHeight: 110, borderWidth: 0 },
  pressed: { transform: [{ scale: 0.97 }] },
  bubble: { width: 46, height: 46, borderRadius: 16, alignItems: 'center', justifyContent: 'center' },
  bubbleWide: { backgroundColor: 'rgba(255,255,255,0.22)' },
  icon: { fontSize: 22 },
  label: { fontWeight: '600', fontSize: 15, lineHeight: 20 },
  labelWide: { color: colors.onPrimary, fontSize: 18, lineHeight: 24 },
});
