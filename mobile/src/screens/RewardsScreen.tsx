import React, { useState } from 'react';
import { ActivityIndicator, ScrollView, StyleSheet } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { useTranslation } from 'react-i18next';

import { AppText, Button, Card, ErrorBanner, Row, Screen, ScreenHeader } from '../components/ui';
import { useApp } from '../contexts/AppContext';
import type { AppStackParams } from '../navigation/RootNavigator';
import { colors, spacing } from '../theme';
import { errorMessage } from './errorMessage';
import { useLoad } from './useLoad';

type Props = NativeStackScreenProps<AppStackParams, 'Rewards'>;

/** Loyalty points (row 43) and, once released, redemption (row 44). */
export function RewardsScreen({ navigation }: Props) {
  const { t } = useTranslation();
  const { api, language, features } = useApp();
  const points = useLoad(() => api.rewards(), [api, language]);
  const canRedeem = (features ?? []).includes('phase2.reward_redemption');
  const options = useLoad(() => (canRedeem ? api.redemptionOptions() : Promise.resolve([])), [api, canRedeem, language]);
  const [failure, setFailure] = useState<unknown>(null);
  const [done, setDone] = useState<string | null>(null);

  const redeem = async (key: string) => {
    setFailure(null);
    try {
      await api.redeem(key);
      setDone(key);
      await points.reload();
    } catch (e) {
      setFailure(e);
    }
  };

  return (
    <Screen testID="rewards">
      <ScrollView contentContainerStyle={styles.content}>
        <ScreenHeader title={t('rewards.title')} onBack={() => navigation.goBack()} />
        {points.loading && !points.data ? <ActivityIndicator color={colors.primary} /> : null}
        <ErrorBanner message={points.error ? errorMessage(points.error, t) : failure ? errorMessage(failure, t) : null} />
        {points.data ? (
          <Card>
            <AppText variant="title" testID="points-balance">
              {t('rewards.balance', { count: points.data.balance })}
            </AppText>
          </Card>
        ) : null}
        {done ? <AppText testID="redeemed">{t('rewards.redeemed')}</AppText> : null}
        {(options.data ?? []).map(o => (
          <Card key={o.key}>
            <AppText variant="heading">{o.title}</AppText>
            <AppText muted>{t('rewards.cost', { count: o.points_cost })}</AppText>
            <Button label={t('rewards.redeem')} onPress={() => redeem(o.key)} testID={`redeem-${o.key}`} />
          </Card>
        ))}
        <AppText variant="heading">{t('rewards.howToEarn')}</AppText>
        {points.data?.how_to_earn.map(rule => (
          <Row key={rule.event} style={styles.row}>
            <AppText style={styles.flex}>{rule.description}</AppText>
            {rule.points ? <AppText>{`+${rule.points}`}</AppText> : null}
          </Row>
        ))}
      </ScrollView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  content: { padding: spacing.lg, gap: spacing.md },
  row: { gap: spacing.sm },
});
