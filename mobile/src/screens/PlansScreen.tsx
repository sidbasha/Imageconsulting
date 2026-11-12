import React, { useState } from 'react';
import { ActivityIndicator, ScrollView, StyleSheet } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { useTranslation } from 'react-i18next';

import type { Checkout } from '../api/client';
import { AppText, Button, Card, ErrorBanner, Screen, ScreenHeader, money } from '../components/ui';
import { useApp } from '../contexts/AppContext';
import type { AppStackParams } from '../navigation/RootNavigator';
import { colors, spacing } from '../theme';
import { PaymentStep } from './checkout';
import { errorMessage } from './errorMessage';
import { useLoad } from './useLoad';

type Props = NativeStackScreenProps<AppStackParams, 'Plans'>;

/** Membership plans (row 35, and row 40 for consultants) and the user's current plan. */
export function PlansScreen({ route, navigation }: Props) {
  const audience = route.params?.audience ?? 'customer';
  const { t } = useTranslation();
  const { api, language } = useApp();
  const plans = useLoad(() => api.plans(audience), [api, audience, language]);
  const mine = useLoad(() => api.subscriptions(), [api, language]);
  const [checkout, setCheckout] = useState<Checkout | null>(null);
  const [failure, setFailure] = useState<unknown>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const run = async (key: string, action: () => Promise<void>) => {
    setBusy(key);
    setFailure(null);
    try {
      await action();
    } catch (e) {
      setFailure(e);
    } finally {
      setBusy(null);
    }
  };
  const live = (mine.data ?? []).filter(s => ['active', 'past_due'].includes(s.status) && s.plan.audience === audience);

  return (
    <Screen testID="plans">
      <ScrollView contentContainerStyle={styles.content}>
        <ScreenHeader title={t(`plans.title.${audience}`)} onBack={() => navigation.goBack()} />
        {plans.loading && !plans.data ? <ActivityIndicator color={colors.primary} /> : null}
        <ErrorBanner message={plans.error ? errorMessage(plans.error, t) : failure ? errorMessage(failure, t) : null} />
        {live.map(s => (
          <Card key={s.id}>
            <AppText variant="heading">{t('plans.current', { plan: s.plan.title })}</AppText>
            <AppText muted>
              {s.cancel_at_period_end
                ? t('plans.endsOn', { date: s.current_period_end?.slice(0, 10) })
                : t('plans.renewsOn', { date: s.current_period_end?.slice(0, 10) })}
            </AppText>
            {!s.cancel_at_period_end ? (
              <Button kind="link" label={t('plans.cancel')} loading={busy === s.id} testID={`cancel-${s.id}`}
                onPress={() => run(s.id, async () => { await api.cancelSubscription(s.id); await mine.reload(); })} />
            ) : null}
          </Card>
        ))}
        {live.length === 0
          ? plans.data?.map(p => (
              <Card key={p.key}>
                <AppText variant="heading">{p.title}</AppText>
                <AppText muted>{p.description}</AppText>
                <AppText>{t(`plans.per.${p.interval}`, { amount: money(p.price_minor, p.currency) })}</AppText>
                <Button label={t('plans.choose')} loading={busy === p.key} testID={`choose-${p.key}`}
                  onPress={() => run(p.key, async () => setCheckout(await api.buyPlan(p.key)))} />
              </Card>
            ))
          : null}
        {checkout ? <PaymentStep checkout={checkout} onPaid={() => { setCheckout(null); mine.reload(); }} /> : null}
      </ScrollView>
    </Screen>
  );
}

const styles = StyleSheet.create({ content: { padding: spacing.lg, gap: spacing.md } });
