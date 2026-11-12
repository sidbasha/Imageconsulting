import React, { useState } from 'react';
import { ActivityIndicator, Linking, ScrollView, StyleSheet } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { useTranslation } from 'react-i18next';

import { AppText, Button, Card, ErrorBanner, Screen, ScreenHeader } from '../components/ui';
import { useApp } from '../contexts/AppContext';
import type { AppStackParams } from '../navigation/RootNavigator';
import { colors, spacing } from '../theme';
import { approximatePosition, type Position } from '../location';
import { errorMessage } from './errorMessage';
import { useLoad } from './useLoad';

type Props = NativeStackScreenProps<AppStackParams, 'Offers'>;

/** Partner offers (rows 49, 50) and vouchers (row 51). */
export function OffersScreen({ route, navigation }: Props) {
  const show = route.params?.show ?? 'offers';
  const { t } = useTranslation();
  const { api, language, features } = useApp();
  const [near, setNear] = useState<Position | null>(null);
  const geo = (features ?? []).includes('phase3.geo_promotions');
  const offers = useLoad(() => (show === 'offers' ? api.promotions('offers', near ?? {}) : Promise.resolve([])), [api, show, language, near]);
  const vouchers = useLoad(() => (show === 'vouchers' ? api.vouchers(near ?? {}) : Promise.resolve([])), [api, show, language, near]);
  const [codes, setCodes] = useState<Record<string, string>>({});
  const [failure, setFailure] = useState<unknown>(null);

  const claim = async (id: string) => {
    setFailure(null);
    try {
      const v = await api.claimVoucher(id);
      setCodes(c => ({ ...c, [id]: v.code ?? '' }));
    } catch (e) {
      setFailure(e);
    }
  };
  const open = async (id: string) => {
    try {
      await Linking.openURL((await api.promotionClick(id)).url);
    } catch (e) {
      setFailure(e);
    }
  };
  const loading = offers.loading || vouchers.loading;
  const error = offers.error || vouchers.error || failure;

  return (
    <Screen testID="offers">
      <ScrollView contentContainerStyle={styles.content}>
        <ScreenHeader title={t(`offers.title.${show}`)} onBack={() => navigation.goBack()} />
        {geo && !near ? (
          <Button kind="link" label={t('offers.nearMe')} testID="offers-near-me"
            onPress={async () => setNear(await approximatePosition())} />
        ) : null}
        {loading ? <ActivityIndicator color={colors.primary} /> : null}
        <ErrorBanner message={error ? errorMessage(error, t) : null} />
        {!loading && (offers.data ?? []).length + (vouchers.data ?? []).length === 0 ? <AppText muted>{t('offers.none')}</AppText> : null}
        {(offers.data ?? []).map(o => (
          <Card key={o.id}>
            <AppText variant="small" muted>
              {t('offers.sponsored', { name: o.advertiser })}
            </AppText>
            <AppText variant="heading">{o.title}</AppText>
            {o.body ? <AppText>{o.body}</AppText> : null}
            {o.has_link ? <Button kind="link" label={t('offers.visit')} onPress={() => open(o.id)} testID={`visit-${o.id}`} /> : null}
          </Card>
        ))}
        {(vouchers.data ?? []).map(v => (
          <Card key={v.id}>
            <AppText variant="small" muted>
              {v.partner}
            </AppText>
            <AppText variant="heading">{v.title}</AppText>
            {v.terms ? <AppText muted>{v.terms}</AppText> : null}
            {codes[v.id] ? (
              <AppText variant="title" testID={`code-${v.id}`} selectable>
                {codes[v.id]}
              </AppText>
            ) : (
              <Button label={t('offers.claim')} onPress={() => claim(v.id)} testID={`claim-${v.id}`} />
            )}
          </Card>
        ))}
      </ScrollView>
    </Screen>
  );
}

const styles = StyleSheet.create({ content: { padding: spacing.lg, gap: spacing.md } });
