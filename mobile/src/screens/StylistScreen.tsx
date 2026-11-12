import React, { useState } from 'react';
import { ActivityIndicator, ScrollView, StyleSheet } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { useTranslation } from 'react-i18next';

import type { Checkout } from '../api/client';
import { AppText, Button, Card, Chips, ErrorBanner, Screen, ScreenHeader, TextField, money } from '../components/ui';
import { useApp } from '../contexts/AppContext';
import type { AppStackParams } from '../navigation/RootNavigator';
import { colors, spacing } from '../theme';
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

  const chosen = data?.services.find(s => s.id === service) ?? null;
  const when = (iso: string) =>
    new Date(iso).toLocaleString(i18n.language === 'ar' ? 'ar-AE' : 'en-AE', { weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });

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

  return (
    <Screen testID="stylist">
      <ScrollView contentContainerStyle={styles.content}>
        <ScreenHeader title={data?.display_name ?? ''} onBack={() => navigation.goBack()} />
        {loading && !data ? <ActivityIndicator color={colors.primary} /> : null}
        <ErrorBanner message={error ? errorMessage(error, t) : failure ? errorMessage(failure, t) : null} />
        {data ? (
          <>
            <AppText>{data.bio}</AppText>
            {data.rating_count ? <AppText muted>{t('stylists.rating', { rating: data.rating_avg.toFixed(1), count: data.rating_count })}</AppText> : null}
            {booked ? (
              <Card>
                <AppText testID="booked">{t('booking.confirmed')}</AppText>
                <Button label={t('booking.mine')} onPress={() => navigation.navigate('Bookings')} testID="go-bookings" />
              </Card>
            ) : checkout ? (
              <PaymentStep checkout={checkout} onPaid={() => { setCheckout(null); setBooked(true); reload(); }} />
            ) : (
              <Card>
                <AppText variant="heading">{t('booking.title')}</AppText>
                <Chips label={t('booking.service')} value={service} onChange={setService} testID="service"
                  options={data.services.map(s => ({ value: s.id, label: `${s.title} · ${money(s.price_minor, s.currency)}` }))} />
                {data.slots.length === 0 ? <AppText muted>{t('booking.noSlots')}</AppText> : null}
                <Chips label={t('booking.time')} value={slot} onChange={setSlot} testID="slot"
                  options={data.slots.map(s => ({ value: s.id, label: when(s.starts_at) }))} />
                {chosen?.mode === 'in_person' ? (
                  <>
                    <TextField label={t('booking.address')} value={line1} onChangeText={setLine1} testID="address-line1" />
                    <TextField label={t('booking.city')} value={city} onChangeText={setCity} testID="address-city" />
                  </>
                ) : null}
                <Button label={t('booking.book')} onPress={() => book(false)} loading={busy} testID="book" />
                {rewardsOn && chosen?.kind === 'consultation' ? (
                  <Button kind="link" label={t('booking.useReward')} onPress={() => book(true)} testID="book-with-reward" />
                ) : null}
              </Card>
            )}
            {data.testimonials.length ? <AppText variant="heading">{t('stylists.testimonials')}</AppText> : null}
            {data.testimonials.map((r, i) => (
              <Card key={i}>
                <AppText>{'★'.repeat(r.rating)}</AppText>
                {r.text ? <AppText>{r.text}</AppText> : null}
              </Card>
            ))}
          </>
        ) : null}
      </ScrollView>
    </Screen>
  );
}

const styles = StyleSheet.create({ content: { padding: spacing.lg, gap: spacing.md } });
