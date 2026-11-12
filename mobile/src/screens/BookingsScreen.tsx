import React, { useState } from 'react';
import { ActivityIndicator, ScrollView, StyleSheet } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { useTranslation } from 'react-i18next';

import { AppText, Button, Card, Chips, ErrorBanner, Row, Screen, ScreenHeader, TextField } from '../components/ui';
import { useApp } from '../contexts/AppContext';
import type { AppStackParams } from '../navigation/RootNavigator';
import { colors, spacing } from '../theme';
import { errorMessage } from './errorMessage';
import { useLoad } from './useLoad';

type Props = NativeStackScreenProps<AppStackParams, 'Bookings'>;

/** The customer's bookings: open the consultation, message the stylist, cancel, review. */
export function BookingsScreen({ navigation }: Props) {
  const { t } = useTranslation();
  const { api, language, features } = useApp();
  const bookings = useLoad(() => api.bookings(), [api, language]);
  const consultations = useLoad(() => api.consultations().catch(() => []), [api, language]);
  const [failure, setFailure] = useState<unknown>(null);
  const [reviewing, setReviewing] = useState<string | null>(null);
  const [rating, setRating] = useState<string | null>('5');
  const [text, setText] = useState('');
  const on = new Set(features ?? []);

  const run = async (action: () => Promise<unknown>) => {
    setFailure(null);
    try {
      await action();
      await bookings.reload();
    } catch (e) {
      setFailure(e);
    }
  };
  const message = async (stylistId: string) => {
    try {
      const thread = await api.openThread(stylistId);
      navigation.navigate('Thread', { id: thread.id, name: thread.with.name });
    } catch (e) {
      setFailure(e);
    }
  };

  return (
    <Screen testID="bookings">
      <ScrollView contentContainerStyle={styles.content}>
        <ScreenHeader title={t('booking.mine')} onBack={() => navigation.goBack()} />
        {bookings.loading && !bookings.data ? <ActivityIndicator color={colors.primary} /> : null}
        <ErrorBanner message={bookings.error ? errorMessage(bookings.error, t) : failure ? errorMessage(failure, t) : null} />
        {bookings.data && bookings.data.length === 0 ? <AppText muted>{t('booking.none')}</AppText> : null}
        {bookings.data?.map(b => {
          const consultation = consultations.data?.find(c => c.booking_id === b.id);
          return (
            <Card key={b.id}>
              <AppText variant="heading">{`${b.service.title} · ${b.stylist.display_name}`}</AppText>
              <AppText muted>{`${b.starts_at.slice(0, 16).replace('T', ' ')} · ${t(`booking.status.${b.status}`, { defaultValue: b.status })}`}</AppText>
              <Row style={styles.row}>
                {consultation ? (
                  <Button kind="link" label={t('booking.openConsultation')} testID={`consultation-${b.id}`}
                    onPress={() => navigation.navigate('Consultation', { id: consultation.id })} />
                ) : null}
                {on.has('phase2.messaging') && ['confirmed', 'completed'].includes(b.status) ? (
                  <Button kind="link" label={t('booking.message')} onPress={() => message(b.stylist.id)} testID={`message-${b.id}`} />
                ) : null}
                {['pending_payment', 'confirmed'].includes(b.status) ? (
                  <Button kind="link" label={t('booking.cancel')} onPress={() => run(() => api.cancelBooking(b.id))} testID={`cancel-${b.id}`} />
                ) : null}
                {b.status === 'completed' && on.has('phase2.testimonials') ? (
                  <Button kind="link" label={t('booking.review')} onPress={() => setReviewing(b.id)} testID={`review-${b.id}`} />
                ) : null}
              </Row>
              {reviewing === b.id ? (
                <>
                  <Chips label={t('booking.rating')} value={rating} onChange={setRating} testID="rating"
                    options={['1', '2', '3', '4', '5'].map(v => ({ value: v, label: '★'.repeat(Number(v)) }))} />
                  <TextField label={t('booking.reviewText')} value={text} onChangeText={setText} multiline testID="review-text" />
                  <Button label={t('booking.sendReview')} testID="send-review"
                    onPress={() => run(async () => { await api.testimonial(b.id, Number(rating), text); setReviewing(null); })} />
                </>
              ) : null}
            </Card>
          );
        })}
      </ScrollView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  content: { padding: spacing.lg, gap: spacing.md },
  row: { gap: spacing.md, flexWrap: 'wrap' },
});
