import React, { useMemo, useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { useTranslation } from 'react-i18next';

import type { Checkout } from '../api/client';
import { AppText, Avatar, Button, Card, Chips, ErrorBanner, Row, Screen, SectionTitle, TextField, money, useDirection } from '../components/ui';
import { useApp } from '../contexts/AppContext';
import type { AppStackParams } from '../navigation/RootNavigator';
import { colors, fonts, gradients, radius, shadows, spacing } from '../theme';
import { PaymentStep } from './checkout';
import { errorMessage } from './errorMessage';
import { useLoad } from './useLoad';

type Props = NativeStackScreenProps<AppStackParams, 'Stylist'>;

/** One stylist's profile, testimonials and booking (rows 18, 19, 45, 46). */
export function StylistScreen({ route, navigation }: Props) {
  const { id } = route.params;
  const { t, i18n } = useTranslation();
  const { api, language, features } = useApp();
  const { data, error, loading, reload } = useLoad(() => api.stylist(id), [api, id, language]);
  const [service, setService] = useState<string | null>(null);
  const [slot, setSlot] = useState<string | null>(null);
  const [line1, setLine1] = useState('');
  const [city, setCity] = useState('');
  const [checkout, setCheckout] = useState<Checkout | null>(null);
  const [booked, setBooked] = useState(false);
  const [failure, setFailure] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const rewardsOn = (features ?? []).includes('phase2.reward_redemption');
  const { rtl } = useDirection();
  const [day, setDay] = useState<string | null>(null);
  const locale = i18n.language === 'ar' ? 'ar-AE' : 'en-AE';

  const chosen = data?.services.find(s => s.id === service) ?? null;

  const book = async (useReward: boolean) => {
    if (!service || !slot) {
      return;
    }
    setBusy(true);
    setFailure(null);
    try {
      const result = await api.book({
        service_id: service, slot_id: slot, use_reward: useReward,
        address: chosen?.mode === 'in_person' ? { line1, city } : undefined,
      });
      if (result.checkout) {
        setCheckout(result.checkout);
      } else {
        setBooked(true);
      }
    } catch (e) {
      setFailure(e);
    } finally {
      setBusy(false);
    }
  };

  // Times grouped by day: pick a day, then a time.
  const days = useMemo(() => {
    const groups: { key: string; label: string; slots: NonNullable<typeof data>['slots'] }[] = [];
    for (const item of data?.slots ?? []) {
      const d = new Date(item.starts_at);
      const key = d.toDateString();
      let group = groups.find(g => g.key === key);
      if (!group) {
        group = { key, label: d.toLocaleDateString(locale, { weekday: 'short', day: 'numeric', month: 'short' }), slots: [] };
        groups.push(group);
      }
      group.slots.push(item);
    }
    return groups;
  }, [data, locale]);
  const activeDay = days.find(d => d.key === day) ?? days[0];

  return (
    <Screen testID="stylist">
      <ScrollView contentContainerStyle={styles.content}>
        <Row>
          <Pressable accessibilityRole="button" accessibilityLabel={t('common.back')} onPress={() => navigation.goBack()} testID="back"
            style={[styles.back, { boxShadow: shadows.soft }]}>
            <Text style={styles.backArrow}>{rtl ? '›' : '‹'}</Text>
          </Pressable>
        </Row>
        {loading && !data ? <ActivityIndicator color={colors.primary} /> : null}
        <ErrorBanner message={error ? errorMessage(error, t) : failure ? errorMessage(failure, t) : null} />
        {data ? (
          <>
            <View style={[styles.hero, { backgroundImage: gradients.hero, boxShadow: shadows.lifted }]}>
              <View style={styles.orb} />
              <Avatar name={data.display_name} size={84} />
              <AppText variant="title" accessibilityRole="header" style={styles.heroName}>{data.display_name}</AppText>
              {data.city ? <Text style={styles.heroCity}>{`📍 ${data.city}`}</Text> : null}
              <Row style={styles.stats}>
                <Stat value={data.rating_count ? `★ ${data.rating_avg.toFixed(1)}` : '—'} label={t('stylists.reviews', { count: data.rating_count })} />
                <View style={styles.statLine} />
                <Stat value={data.years_experience !== null ? String(data.years_experience) : '—'} label={t('stylists.years')} />
                <View style={styles.statLine} />
                <Stat value={String(data.languages.length || 1)} label={t('stylists.languages')} />
              </Row>
            </View>
            {data.bio ? <AppText style={styles.bio}>{data.bio}</AppText> : null}

            {booked ? (
              <Card>
                <AppText variant="heading" testID="booked">{t('booking.confirmed')}</AppText>
                <Button label={t('booking.mine')} onPress={() => navigation.navigate('Bookings')} testID="go-bookings" />
              </Card>
            ) : checkout ? (
              <PaymentStep checkout={checkout} onPaid={() => { setCheckout(null); setBooked(true); reload(); }} />
            ) : (
              <>
                <SectionTitle>{t('booking.chooseService')}</SectionTitle>
                {data.services.map(sv => {
                  const selected = sv.id === service;
                  return (
                    <Pressable key={sv.id} accessibilityRole="radio" accessibilityState={{ selected }} accessibilityLabel={sv.title}
                      testID={`service-${sv.id}`} onPress={() => setService(sv.id)}
                      style={[styles.service, { boxShadow: shadows.soft }, selected && styles.serviceOn]}>
                      <View style={styles.flex}>
                        <AppText style={[styles.serviceTitle, selected && styles.serviceTitleOn]}>{sv.title}</AppText>
                        <AppText variant="small" muted>
                          {`${sv.duration_minutes >= 120 ? t('booking.hours', { count: Math.round(sv.duration_minutes / 60) }) : t('booking.minutes', { count: sv.duration_minutes })} · ${t(`booking.mode.${sv.mode}`)}`}
                        </AppText>
                      </View>
                      <Text style={[styles.price, selected && styles.priceOn]}>{money(sv.price_minor, sv.currency)}</Text>
                    </Pressable>
                  );
                })}

                <SectionTitle>{t('booking.chooseTime')}</SectionTitle>
                {days.length === 0 ? <AppText muted>{t('booking.noSlots')}</AppText> : null}
                <Chips scroll value={activeDay?.key ?? null} onChange={setDay} testID="day" options={days.map(d => ({ value: d.key, label: d.label }))} />
                <Row style={styles.times}>
                  {activeDay?.slots.map(sl => {
                    const selected = sl.id === slot;
                    return (
                      <Pressable key={sl.id} accessibilityRole="radio" accessibilityState={{ selected }} testID={`slot-${sl.id}`}
                        accessibilityLabel={new Date(sl.starts_at).toLocaleString(locale)} onPress={() => setSlot(sl.id)}
                        style={[styles.time, selected && { backgroundImage: gradients.primary, borderColor: colors.primary }]}>
                        <Text style={[styles.timeText, selected && styles.timeTextOn]}>
                          {new Date(sl.starts_at).toLocaleTimeString(locale, { hour: '2-digit', minute: '2-digit' })}
                        </Text>
                      </Pressable>
                    );
                  })}
                </Row>
                {chosen?.mode === 'in_person' ? (
                  <Card>
                    <TextField label={t('booking.address')} value={line1} onChangeText={setLine1} testID="address-line1" />
                    <TextField label={t('booking.city')} value={city} onChangeText={setCity} testID="address-city" />
                  </Card>
                ) : null}
                <Button label={chosen ? `${t('booking.book')} · ${money(chosen.price_minor, chosen.currency)}` : t('booking.book')}
                  onPress={() => book(false)} loading={busy} testID="book" />
                {rewardsOn && chosen?.kind === 'consultation' ? (
                  <Button kind="soft" label={t('booking.useReward')} onPress={() => book(true)} testID="book-with-reward" />
                ) : null}
              </>
            )}

            {data.testimonials.length ? <SectionTitle>{t('stylists.testimonials')}</SectionTitle> : null}
            {data.testimonials.map((r, i) => (
              <Card key={i}>
                <Text style={styles.quoteMark}>“</Text>
                {r.text ? <AppText style={styles.quote}>{r.text}</AppText> : null}
                <Text style={styles.stars}>{'★'.repeat(r.rating)}</Text>
              </Card>
            ))}
          </>
        ) : null}
      </ScrollView>
    </Screen>
  );
}

function Stat({ value, label }: { value: string; label: string }) {
  return (
    <View style={styles.stat}>
      <Text style={styles.statValue}>{value}</Text>
      <Text style={styles.statLabel}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  content: { padding: spacing.lg, gap: spacing.md, paddingBottom: spacing.xl * 2 },
  back: { width: 42, height: 42, borderRadius: 21, backgroundColor: colors.surface, alignItems: 'center', justifyContent: 'center' },
  backArrow: { fontSize: 28, lineHeight: 30, color: colors.primary, fontWeight: '300', marginTop: -2 },
  hero: { borderRadius: radius.xl, padding: spacing.lg, alignItems: 'center', gap: spacing.sm, overflow: 'hidden' },
  orb: { position: 'absolute', width: 260, height: 260, borderRadius: 130, backgroundColor: 'rgba(255,255,255,0.10)', top: -120, right: -80 },
  heroName: { color: colors.onPrimary, textAlign: 'center', marginTop: spacing.xs },
  heroCity: { color: 'rgba(255,255,255,0.9)', fontSize: 14 },
  stats: { marginTop: spacing.sm, backgroundColor: 'rgba(255,255,255,0.16)', borderRadius: radius.md, paddingVertical: spacing.sm,
    paddingHorizontal: spacing.md, alignItems: 'center', gap: spacing.md },
  stat: { alignItems: 'center', minWidth: 64 },
  statValue: { color: colors.onPrimary, fontSize: 17, fontWeight: '700' },
  statLabel: { color: 'rgba(255,255,255,0.85)', fontSize: 11, letterSpacing: 0.6, textTransform: 'uppercase' },
  statLine: { width: 1, height: 28, backgroundColor: 'rgba(255,255,255,0.35)' },
  bio: { lineHeight: 24, color: colors.text },
  service: { flexDirection: 'row', alignItems: 'center', gap: spacing.md, backgroundColor: colors.surface, borderRadius: radius.md,
    padding: spacing.md, borderWidth: 1.5, borderColor: 'transparent' },
  serviceOn: { borderColor: colors.primary, backgroundColor: colors.primarySoft },
  serviceTitle: { fontWeight: '600' },
  serviceTitleOn: { color: colors.primaryDeep },
  price: { fontWeight: '700', color: colors.text },
  priceOn: { color: colors.primaryDeep },
  times: { gap: spacing.sm, flexWrap: 'wrap' },
  time: { width: '30.5%', minHeight: 46, borderRadius: radius.sm + 4, borderWidth: 1.5, borderColor: colors.border,
    backgroundColor: colors.surface, alignItems: 'center', justifyContent: 'center' },
  timeText: { fontWeight: '600', color: colors.text },
  timeTextOn: { color: colors.onPrimary },
  quoteMark: { fontFamily: fonts.display, fontSize: 44, lineHeight: 44, color: colors.gold, marginBottom: -12 },
  quote: { fontStyle: 'italic', lineHeight: 24 },
  stars: { color: colors.gold, letterSpacing: 2 },
});
