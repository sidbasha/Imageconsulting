import React, { useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { useTranslation } from 'react-i18next';

import { AppText, Avatar, Chips, ErrorBanner, Rating, Row, Screen, ScreenHeader, Tag, TextField, money } from '../components/ui';
import { approximatePosition, type Position } from '../location';
import { useApp } from '../contexts/AppContext';
import type { AppStackParams } from '../navigation/RootNavigator';
import { colors, gradients, radius, shadows, spacing } from '../theme';
import { errorMessage } from './errorMessage';
import { useLoad } from './useLoad';

type Props = NativeStackScreenProps<AppStackParams, 'Stylists'>;
const RADIUS_KM = 25;
const KINDS = ['consultation', 'occasion_audit', 'wardrobe_audit', 'makeup_audit', 'expert_color', 'personal_shopper_day'];

/** Verified stylists (row 18), filtered by service and city. */
export function StylistsScreen({ route, navigation }: Props) {
  const { t } = useTranslation();
  const { api, language, features } = useApp();
  const [kind, setKind] = useState<string | null>(route.params?.kind ?? null);
  const [city, setCity] = useState('');
  const [near, setNear] = useState<Position | null>(null);
  const [locating, setLocating] = useState(false);
  const [noLocation, setNoLocation] = useState(false);
  const locationOn = (features ?? []).includes('phase3.location_discovery');
  const { data, error, loading } = useLoad(
    () => api.stylists({ kind: kind ?? undefined, city: near ? undefined : city.trim() || undefined,
      ...(near ? { lat: near.lat, lng: near.lng, radius_km: RADIUS_KM } : {}) }),
    [api, kind, city, near, language],
  );

  const toggleNear = async () => {
    if (near) {
      setNear(null);
      return;
    }
    setLocating(true);
    const position = await approximatePosition();
    setLocating(false);
    setNoLocation(!position);
    setNear(position);
  };

  return (
    <Screen testID="stylists">
      <ScrollView contentContainerStyle={styles.content}>
        <ScreenHeader title={t('stylists.title')} onBack={() => navigation.goBack()} />
        <AppText muted>{t('stylists.intro')}</AppText>
        <Chips scroll value={kind} onChange={v => setKind(v === kind ? null : v)} testID="kind"
          options={KINDS.map(k => ({ value: k, label: t(`services.${k}`) }))} />
        <Row style={styles.searchRow}>
          {!near ? (
            <View style={styles.flex}>
              <TextField label={t('stylists.city')} value={city} onChangeText={setCity} testID="city" placeholder={t('stylists.cityHint')} />
            </View>
          ) : (
            <View style={styles.flex}>
              <Tag label={t('stylists.showingNear')} tone="gold" />
            </View>
          )}
          {locationOn ? (
            <Pressable accessibilityRole="button" accessibilityLabel={near ? t('stylists.anywhere') : t('stylists.nearMe')} onPress={toggleNear}
              testID="near-me" style={({ pressed }) => [styles.nearPill, near && styles.nearPillOn, { boxShadow: shadows.soft }, pressed && styles.pressed]}>
              {locating ? <ActivityIndicator color={colors.primary} /> : (
                <Text style={[styles.nearText, near && styles.nearTextOn]}>{near ? t('stylists.anywhere') : `📍 ${t('stylists.nearMe')}`}</Text>
              )}
            </Pressable>
          ) : null}
        </Row>
        {noLocation ? <AppText variant="small" muted testID="no-location">{t('stylists.noLocation')}</AppText> : null}
        {loading && !data ? <ActivityIndicator color={colors.primary} /> : null}
        <ErrorBanner message={error ? errorMessage(error, t) : null} />
        {data && data.length === 0 ? <AppText muted>{t('stylists.none')}</AppText> : null}
        {data?.map(s => {
          const from = s.services.length ? Math.min(...s.services.map(x => x.price_minor)) : null;
          return (
            <Pressable key={s.id} accessibilityRole="button" accessibilityLabel={s.display_name} testID={`stylist-${s.id}`}
              onPress={() => navigation.navigate('Stylist', { id: s.id })}
              style={({ pressed }) => [styles.card, { boxShadow: shadows.soft, backgroundImage: gradients.card }, pressed && styles.pressed]}>
              {s.promoted ? (
                <View style={[styles.ribbon, { backgroundImage: gradients.gold }]}>
                  <Text style={styles.ribbonText}>{t('stylists.featured')}</Text>
                </View>
              ) : null}
              <Row style={styles.cardTop}>
                <Avatar name={s.display_name} size={64} />
                <View style={styles.flex}>
                  <AppText variant="heading" style={styles.name}>{s.display_name}</AppText>
                  <Row style={styles.meta}>
                    {s.city ? <AppText variant="small" muted>{`📍 ${s.city}`}</AppText> : null}
                    {s.distance_km !== null ? <AppText variant="small" muted>{t('stylists.distance', { km: s.distance_km })}</AppText> : null}
                  </Row>
                  <Rating value={s.rating_avg} count={s.rating_count} />
                </View>
              </Row>
              {s.bio ? <AppText muted numberOfLines={2} style={styles.bio}>{s.bio}</AppText> : null}
              <Row style={styles.tags}>
                {s.services.slice(0, 3).map(sv => <Tag key={sv.id} label={t(`services.${sv.kind}`)} tone="lilac" />)}
              </Row>
              <View style={styles.divider} />
              <Row style={styles.footer}>
                <AppText variant="small" muted style={styles.flex}>
                  {from !== null ? t('stylists.from', { price: money(from, s.services[0].currency) }) : ''}
                </AppText>
                <AppText style={styles.view}>{t('stylists.view')} ›</AppText>
              </Row>
            </Pressable>
          );
        })}
      </ScrollView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  content: { padding: spacing.lg, gap: spacing.md, paddingBottom: spacing.xl * 2 },
  searchRow: { gap: spacing.sm, alignItems: 'flex-end' },
  nearPill: { minHeight: 54, paddingHorizontal: spacing.md, borderRadius: radius.pill, backgroundColor: colors.surface, alignItems: 'center', justifyContent: 'center' },
  nearPillOn: { backgroundColor: colors.primarySoft },
  nearText: { color: colors.primary, fontWeight: '600', fontSize: 14 },
  nearTextOn: { color: colors.primaryDeep },
  card: { backgroundColor: colors.surface, borderRadius: radius.lg, padding: spacing.md + 2, gap: spacing.sm + 2, overflow: 'hidden',
    borderWidth: 1, borderColor: 'rgba(239, 226, 226, 0.7)' },
  pressed: { transform: [{ scale: 0.985 }] },
  ribbon: { position: 'absolute', top: 14, right: -34, width: 130, paddingVertical: 3, transform: [{ rotate: '35deg' }], alignItems: 'center' },
  ribbonText: { color: colors.onPrimary, fontSize: 11, fontWeight: '700', letterSpacing: 1 },
  cardTop: { gap: spacing.md, alignItems: 'center' },
  name: { fontSize: 19 },
  meta: { gap: spacing.sm, flexWrap: 'wrap' },
  bio: { lineHeight: 21 },
  tags: { gap: 6, flexWrap: 'wrap' },
  divider: { height: 1, backgroundColor: colors.border, marginVertical: 2 },
  footer: { alignItems: 'center' },
  view: { color: colors.primary, fontWeight: '700' },
});
