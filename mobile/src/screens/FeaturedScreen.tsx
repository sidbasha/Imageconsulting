import React, { useState } from 'react';
import { ScrollView, StyleSheet } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { useTranslation } from 'react-i18next';

import type { Checkout } from '../api/client';
import { AppText, Button, Card, Chips, ErrorBanner, Screen, ScreenHeader } from '../components/ui';
import { useApp } from '../contexts/AppContext';
import type { AppStackParams } from '../navigation/RootNavigator';
import { spacing } from '../theme';
import { PaymentStep } from './checkout';
import { errorMessage } from './errorMessage';
import { useLoad } from './useLoad';

type Props = NativeStackScreenProps<AppStackParams, 'Featured'>;

/** Paid featured placement in stylist search (row 42). Reviewed by an administrator before it runs. */
export function FeaturedScreen({ navigation }: Props) {
  const { t } = useTranslation();
  const { api } = useApp();
  const mine = useLoad(() => api.myFeatured(), [api]);
  const [days, setDays] = useState<string | null>('7');
  const [checkout, setCheckout] = useState<Checkout | null>(null);
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<unknown>(null);

  const buy = async () => {
    setBusy(true);
    setFailure(null);
    try {
      setCheckout((await api.buyFeatured(new Date().toISOString(), Number(days))).checkout);
    } catch (e) {
      setFailure(e);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Screen testID="featured">
      <ScrollView contentContainerStyle={styles.content}>
        <ScreenHeader title={t('featured.title')} onBack={() => navigation.goBack()} />
        <AppText muted>{t('featured.intro')}</AppText>
        <ErrorBanner message={mine.error ? errorMessage(mine.error, t) : failure ? errorMessage(failure, t) : null} />
        {(mine.data ?? []).map(c => (
          <Card key={c.id}>
            <AppText>{`${c.starts_at.slice(0, 10)} → ${c.ends_at.slice(0, 10)}`}</AppText>
            <AppText muted testID={`campaign-${c.id}`}>{t(`featured.status.${c.status}`, { defaultValue: c.status })}</AppText>
            {c.status === 'active' ? <AppText variant="small" muted>{t('featured.seen', { count: c.impressions })}</AppText> : null}
          </Card>
        ))}
        {checkout ? (
          <PaymentStep checkout={checkout} onPaid={() => { setCheckout(null); mine.reload(); }} />
        ) : (
          <Card>
            <Chips label={t('featured.days')} value={days} onChange={setDays} testID="days"
              options={['7', '14', '30'].map(d => ({ value: d, label: t('featured.daysOption', { count: Number(d) }) }))} />
            <Button label={t('featured.buy')} onPress={buy} loading={busy} testID="buy-featured" />
          </Card>
        )}
      </ScrollView>
    </Screen>
  );
}

const styles = StyleSheet.create({ content: { padding: spacing.lg, gap: spacing.md } });
