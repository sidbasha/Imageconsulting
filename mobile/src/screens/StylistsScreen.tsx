import React, { useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, StyleSheet } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { useTranslation } from 'react-i18next';

import { AppText, Card, Chips, ErrorBanner, Screen, ScreenHeader, TextField, money } from '../components/ui';
import { useApp } from '../contexts/AppContext';
import type { AppStackParams } from '../navigation/RootNavigator';
import { colors, spacing } from '../theme';
import { errorMessage } from './errorMessage';
import { useLoad } from './useLoad';

type Props = NativeStackScreenProps<AppStackParams, 'Stylists'>;
const KINDS = ['consultation', 'occasion_audit', 'wardrobe_audit', 'makeup_audit', 'expert_color', 'personal_shopper_day'];

/** Verified stylists (row 18), filtered by service and city. */
export function StylistsScreen({ route, navigation }: Props) {
  const { t } = useTranslation();
  const { api, language } = useApp();
  const [kind, setKind] = useState<string | null>(route.params?.kind ?? null);
  const [city, setCity] = useState('');
  const { data, error, loading } = useLoad(() => api.stylists({ kind: kind ?? undefined, city: city.trim() || undefined }), [api, kind, city, language]);

  return (
    <Screen testID="stylists">
      <ScrollView contentContainerStyle={styles.content}>
        <ScreenHeader title={t('stylists.title')} onBack={() => navigation.goBack()} />
        <Chips value={kind} onChange={v => setKind(v === kind ? null : v)} testID="kind"
          options={KINDS.map(k => ({ value: k, label: t(`services.${k}`) }))} />
        <TextField label={t('stylists.city')} value={city} onChangeText={setCity} testID="city" />
        {loading && !data ? <ActivityIndicator color={colors.primary} /> : null}
        <ErrorBanner message={error ? errorMessage(error, t) : null} />
        {data && data.length === 0 ? <AppText muted>{t('stylists.none')}</AppText> : null}
        {data?.map(s => (
          <Pressable key={s.id} accessibilityRole="button" accessibilityLabel={s.display_name} testID={`stylist-${s.id}`}
            onPress={() => navigation.navigate('Stylist', { id: s.id })}>
            <Card>
              {s.promoted ? <AppText variant="small" muted>{t('stylists.featured')}</AppText> : null}
              <AppText variant="heading">{s.display_name}</AppText>
              <AppText muted>
                {[s.city, s.rating_count ? t('stylists.rating', { rating: s.rating_avg.toFixed(1), count: s.rating_count }) : null,
                  s.distance_km !== null ? t('stylists.distance', { km: s.distance_km }) : null].filter(Boolean).join(' · ')}
              </AppText>
              <AppText variant="small">
                {s.services.map(sv => `${sv.title} (${money(sv.price_minor, sv.currency)})`).join(', ')}
              </AppText>
            </Card>
          </Pressable>
        ))}
      </ScrollView>
    </Screen>
  );
}

const styles = StyleSheet.create({ content: { padding: spacing.lg, gap: spacing.md } });
