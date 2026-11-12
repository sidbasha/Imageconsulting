import React from 'react';
import { ActivityIndicator, ScrollView, StyleSheet, View } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { useTranslation } from 'react-i18next';

import { PaletteView } from '../components/PaletteView';
import { AppText, Button, Card, ErrorBanner, Screen, ScreenHeader, Tag } from '../components/ui';
import { useApp } from '../contexts/AppContext';
import type { AppStackParams } from '../navigation/RootNavigator';
import { colors, radius, spacing } from '../theme';
import { errorMessage } from './errorMessage';
import { useLoad } from './useLoad';

/** The customer's digital palette, from the most reliable source she has (expert report, own draping, photo). */
export function MyPaletteScreen({ navigation }: NativeStackScreenProps<AppStackParams, 'MyPalette'>) {
  const { t } = useTranslation();
  const { api, language, features } = useApp();
  const palette = useLoad(() => api.myPalette(), [api, language]);
  const reload = palette.reload;
  React.useEffect(() => navigation.addListener('focus', () => { reload(); }), [navigation, reload]);
  const on = new Set(features ?? []);
  const p = palette.data;

  return (
    <Screen testID="my-palette">
      <ScrollView contentContainerStyle={styles.content}>
        <ScreenHeader title={t('myPalette.title')} onBack={() => navigation.goBack()} />
        {palette.loading && p === undefined ? <ActivityIndicator color={colors.primary} /> : null}
        <ErrorBanner message={palette.error ? errorMessage(palette.error, t) : null} />

        {p === null ? (
          <Card>
            <AppText variant="heading" testID="palette-none">{t('myPalette.none')}</AppText>
            <AppText muted>{t('myPalette.noneNote')}</AppText>
            <Button label={t('selfDraping.title')} onPress={() => navigation.navigate('SelfDraping')} testID="go-self-draping" />
            <Button kind="soft" label={t('myPalette.photo')} onPress={() => navigation.navigate('PhotoAnalysis', { kind: 'seasonal_color' })}
              testID="go-photo" />
          </Card>
        ) : null}

        {p ? (
          <>
            <View style={styles.basis}>
              <Tag label={t(`myPalette.basis.${p.basis}`)} tone={p.basis === 'expert' ? 'gold' : 'rose'} />
              <AppText variant="small" muted>{p.since.slice(0, 10)}</AppText>
            </View>
            {p.custom_palette?.length ? (
              <Card>
                <AppText variant="heading">{t('myPalette.consultantPicks')}</AppText>
                <View style={styles.picks}>
                  {p.custom_palette.map(hex => <View key={hex} style={[styles.pick, { backgroundColor: hex }]} accessibilityLabel={hex} />)}
                </View>
              </Card>
            ) : null}
            <PaletteView type={p} testID="my-palette-view" />
            {p.basis !== 'expert' ? (
              <>
                <Button kind="soft" label={t('myPalette.redo')} onPress={() => navigation.navigate('SelfDraping')} testID="redo-self-draping" />
                {on.has('phase2.expert_color_analysis') ? (
                  <Button kind="link" label={t('myPalette.expert')} onPress={() => navigation.navigate('Stylists', { kind: 'expert_color' })}
                    testID="go-expert" />
                ) : null}
              </>
            ) : null}
          </>
        ) : null}
      </ScrollView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  content: { padding: spacing.lg, gap: spacing.md, paddingBottom: spacing.xl * 2 },
  basis: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm },
  picks: { flexDirection: 'row', flexWrap: 'wrap', gap: 6 },
  pick: { width: 40, height: 40, borderRadius: radius.sm },
});
