import React, { useState } from 'react';
import { Linking, View } from 'react-native';
import { useTranslation } from 'react-i18next';

import type { Checkout } from '../api/client';
import { AppText, Button, Card, ErrorBanner, money } from '../components/ui';
import { useApp } from '../contexts/AppContext';
import { errorMessage } from './errorMessage';

/**
 * After an order is created: in production the customer pays on the gateway's
 * own page (card details never pass through the app). With the development
 * sandbox there is no such page, so a test button completes the payment the
 * way the gateway's webhook would. That button never appears in a release build.
 */
export function PaymentStep({ checkout, onPaid }: { checkout: Checkout; onPaid: () => void }) {
  const { t } = useTranslation();
  const { api } = useApp();
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<unknown>(null);
  if (checkout.status === 'paid' || !checkout.payment_url) {
    return null;
  }
  const sandbox = checkout.provider === 'sandbox';
  const payInSandbox = async () => {
    setBusy(true);
    setFailure(null);
    try {
      await api.sandboxPay(checkout.payment_url!);
      onPaid();
    } catch (e) {
      setFailure(e);
    } finally {
      setBusy(false);
    }
  };
  return (
    <Card>
      <AppText>{t('checkout.toPay', { amount: money(checkout.amount_minor, checkout.currency) })}</AppText>
      <ErrorBanner message={failure ? errorMessage(failure, t) : null} />
      {sandbox && __DEV__ ? (
        <View>
          <AppText variant="small" muted>
            {t('checkout.sandboxNote')}
          </AppText>
          <Button label={t('checkout.sandboxPay')} onPress={payInSandbox} loading={busy} testID="sandbox-pay" />
        </View>
      ) : (
        <Button label={t('checkout.pay')} onPress={() => Linking.openURL(api.absolute(checkout.payment_url!))} testID="pay" />
      )}
    </Card>
  );
}
