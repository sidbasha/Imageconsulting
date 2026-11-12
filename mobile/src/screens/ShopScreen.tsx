import React, { useState } from 'react';
import { ActivityIndicator, ScrollView, StyleSheet } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { useTranslation } from 'react-i18next';

import type { Checkout, Product } from '../api/client';
import { AppText, Button, Card, ErrorBanner, Screen, ScreenHeader, TextField, money } from '../components/ui';
import { useApp } from '../contexts/AppContext';
import type { AppStackParams } from '../navigation/RootNavigator';
import { colors, spacing } from '../theme';
import { PaymentStep } from './checkout';
import { errorMessage } from './errorMessage';
import { useLoad } from './useLoad';

type Props = NativeStackScreenProps<AppStackParams, 'Shop'>;
const FIELDS = ['full_name', 'phone', 'line1', 'city'] as const;

/** Physical products delivered to the customer (row 48). */
export function ShopScreen({ navigation }: Props) {
  const { t } = useTranslation();
  const { api, language } = useApp();
  const { data, error, loading } = useLoad(() => api.products('physical'), [api, language]);
  const [chosen, setChosen] = useState<Product | null>(null);
  const [address, setAddress] = useState<Record<string, string>>({});
  const [checkout, setCheckout] = useState<Checkout | null>(null);
  const [failure, setFailure] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const [paid, setPaid] = useState(false);

  const order = async () => {
    if (!chosen) {
      return;
    }
    setBusy(true);
    setFailure(null);
    try {
      setCheckout(await api.buyProduct(chosen.key, 1, { ...address, country_code: 'AE' }));
    } catch (e) {
      setFailure(e);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Screen testID="shop">
      <ScrollView contentContainerStyle={styles.content}>
        <ScreenHeader title={t('shop.title')} onBack={() => navigation.goBack()} />
        {loading && !data ? <ActivityIndicator color={colors.primary} /> : null}
        <ErrorBanner message={error ? errorMessage(error, t) : failure ? errorMessage(failure, t) : null} />
        {paid ? <AppText testID="ordered">{t('shop.ordered')}</AppText> : null}
        {data?.map(p => (
          <Card key={p.key}>
            <AppText variant="heading">{p.title}</AppText>
            <AppText muted>{p.description}</AppText>
            <AppText>{money(p.price_minor, p.currency)}</AppText>
            <Button kind="link" label={t('shop.order')} onPress={() => { setChosen(p); setCheckout(null); }} testID={`order-${p.key}`} />
          </Card>
        ))}
        {chosen && !checkout ? (
          <Card>
            <AppText variant="heading">{t('shop.delivery', { item: chosen.title })}</AppText>
            {FIELDS.map(f => (
              <TextField key={f} label={t(`shop.fields.${f}`)} value={address[f] ?? ''} testID={`address-${f}`}
                onChangeText={v => setAddress(a => ({ ...a, [f]: v }))} />
            ))}
            <Button label={t('shop.continue')} onPress={order} loading={busy} testID="place-order" />
          </Card>
        ) : null}
        {checkout ? <PaymentStep checkout={checkout} onPaid={() => { setCheckout(null); setChosen(null); setPaid(true); }} /> : null}
      </ScrollView>
    </Screen>
  );
}

const styles = StyleSheet.create({ content: { padding: spacing.lg, gap: spacing.md } });
