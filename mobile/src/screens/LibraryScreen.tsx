import React, { useState } from 'react';
import { ActivityIndicator, Linking, ScrollView, StyleSheet, View } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { useTranslation } from 'react-i18next';

import type { Checkout, Product } from '../api/client';
import { AppText, Button, Card, ErrorBanner, Row, Screen, ScreenHeader, money } from '../components/ui';
import { useApp } from '../contexts/AppContext';
import type { AppStackParams } from '../navigation/RootNavigator';
import { colors, spacing } from '../theme';
import { PaymentStep } from './checkout';
import { errorMessage } from './errorMessage';
import { useLoad } from './useLoad';

type Props = NativeStackScreenProps<AppStackParams, 'Library'>;

/** Guides and reports (rows 37-39): free ones to add, paid ones to buy, owned ones to open as PDF. */
export function LibraryScreen({ route, navigation }: Props) {
  const kind = route.params?.kind ?? 'guide';
  const { t } = useTranslation();
  const { api, language } = useApp();
  const { data, error, loading, reload } = useLoad(() => api.products(kind), [api, kind, language]);
  const [busy, setBusy] = useState<string | null>(null);
  const [failure, setFailure] = useState<unknown>(null);
  const [checkout, setCheckout] = useState<{ key: string; checkout: Checkout } | null>(null);

  const act = async (key: string, action: () => Promise<unknown>) => {
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

  const open = (p: Product) =>
    act(p.key, async () => {
      const { path } = await api.downloadLink(p.key);
      await Linking.openURL(api.absolute(path));
    });
  const claim = (p: Product) => act(p.key, async () => { await api.claimFree(p.key); await reload(); });
  const buy = (p: Product) => act(p.key, async () => setCheckout({ key: p.key, checkout: await api.buyProduct(p.key) }));

  return (
    <Screen testID="library">
      <ScrollView contentContainerStyle={styles.content}>
        <ScreenHeader title={t(`library.title.${kind}`)} onBack={() => navigation.goBack()} />
        {loading && !data ? <ActivityIndicator color={colors.primary} accessibilityLabel={t('common.loading')} /> : null}
        <ErrorBanner message={error ? errorMessage(error, t) : failure ? errorMessage(failure, t) : null} />
        {data?.map(p => (
          <Card key={p.key}>
            <AppText variant="heading">{p.title}</AppText>
            <AppText muted>{p.description}</AppText>
            <Row style={styles.row}>
              <AppText style={styles.flex}>{p.is_free ? t('library.free') : money(p.price_minor, p.currency)}</AppText>
              {p.owned ? (
                <Button kind="link" label={t('library.open')} onPress={() => open(p)} loading={busy === p.key} testID={`open-${p.key}`} />
              ) : p.is_free ? (
                <Button kind="link" label={t('library.add')} onPress={() => claim(p)} loading={busy === p.key} testID={`claim-${p.key}`} />
              ) : (
                <Button kind="link" label={t('library.buy')} onPress={() => buy(p)} loading={busy === p.key} testID={`buy-${p.key}`} />
              )}
            </Row>
            {checkout?.key === p.key ? (
              <PaymentStep checkout={checkout.checkout} onPaid={() => { setCheckout(null); reload(); }} />
            ) : null}
          </Card>
        ))}
        {kind === 'guide' ? (
          <View>
            <Button kind="link" label={t('library.reports')} onPress={() => navigation.push('Library', { kind: 'report' })} testID="go-reports" />
          </View>
        ) : null}
      </ScrollView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  content: { padding: spacing.lg, gap: spacing.md },
  row: { gap: spacing.sm, alignItems: 'center' },
});
