import React, { useCallback, useState } from 'react';
import { ActivityIndicator, Pressable, RefreshControl, ScrollView, StyleSheet, View } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { useTranslation } from 'react-i18next';

import { AppText, Button, ErrorBanner, Row, Screen } from '../components/ui';
import { useApp } from '../contexts/AppContext';
import { visibleSections, type Entry } from '../navigation/registry';
import type { AppStackParams } from '../navigation/RootNavigator';
import { colors, radius, spacing } from '../theme';
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
        <Row style={styles.top}>
          <View style={styles.flex}>
            <AppText variant="title" accessibilityRole="header">
              {t('home.greeting', { name: user?.full_name ?? '' })}
            </AppText>
            <AppText muted>{t('home.subtitle')}</AppText>
          </View>
          <Button kind="link" label={t('home.settings')} onPress={() => navigation.navigate('Settings')} testID="open-settings" />
        </Row>

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
            <AppText variant="heading" accessibilityRole="header">
              {t(`groups.${section.group}`)}
            </AppText>
            {section.entries.map(entry => (
              <EntryCard key={entry.id} entry={entry} onOpen={screen => navigation.navigate(screen as never)} />
            ))}
          </View>
        ))}
      </ScrollView>
    </Screen>
  );
}

function EntryCard({ entry, onOpen }: { entry: Entry; onOpen: (screen: string) => void }) {
  const { t } = useTranslation();
  const ready = !!entry.screen;
  const label = t(`entries.${entry.id}`);
  return (
    <Pressable
      testID={`entry-${entry.id}`}
      accessibilityRole="button"
      accessibilityLabel={ready ? label : `${label}, ${t('common.inDevelopment')}`}
      accessibilityState={{ disabled: !ready }}
      disabled={!ready}
      onPress={() => entry.screen && onOpen(entry.screen)}
      style={styles.card}>
      <Row style={styles.cardRow}>
        <AppText style={styles.flex}>{label}</AppText>
        {ready ? null : (
          <View style={styles.badge}>
            <AppText variant="small" muted>
              {t('common.inDevelopment')}
            </AppText>
          </View>
        )}
      </Row>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  content: { padding: spacing.lg, gap: spacing.lg },
  top: { gap: spacing.md, alignItems: 'flex-start' },
  gap: { gap: spacing.sm },
  card: {
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.border,
    padding: spacing.md,
    minHeight: 56,
    justifyContent: 'center',
  },
  cardRow: { gap: spacing.sm },
  badge: { backgroundColor: colors.badge, borderRadius: 999, paddingHorizontal: spacing.sm, paddingVertical: 2 },
});
