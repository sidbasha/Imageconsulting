import React, { useState } from 'react';
import { ActivityIndicator, ScrollView, StyleSheet, Text, View } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { useTranslation } from 'react-i18next';

import { AppText, Button, Card, ErrorBanner, Row, Screen, ScreenHeader, SectionTitle, Tag } from '../components/ui';
import { useApp } from '../contexts/AppContext';
import type { AppStackParams } from '../navigation/RootNavigator';
import { colors, fonts, gradients, radius, shadows, spacing } from '../theme';
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
          <View style={[styles.member, { backgroundImage: gradients.hero, boxShadow: shadows.lifted }]}>
            <View style={styles.orb} />
            <Text style={styles.memberKicker}>{t('rewards.cardTitle')}</Text>
            <Text style={styles.memberPoints} testID="points-balance">{t('rewards.balance', { count: points.data.balance })}</Text>
            <View style={[styles.memberLine, { backgroundImage: gradients.gold }]} />
            <Text style={styles.memberNote}>{t('rewards.cardNote')}</Text>
          </View>
        ) : null}
        {done ? <AppText testID="redeemed">{t('rewards.redeemed')}</AppText> : null}
        {(options.data ?? []).map(o => (
          <Card key={o.key}>
            <AppText variant="heading">{o.title}</AppText>
            <AppText muted>{t('rewards.cost', { count: o.points_cost })}</AppText>
            <Button label={t('rewards.redeem')} onPress={() => redeem(o.key)} testID={`redeem-${o.key}`} />
          </Card>
        ))}
        <SectionTitle>{t('rewards.howToEarn')}</SectionTitle>
        <Card>
          {points.data?.how_to_earn.map((rule, i) => (
            <View key={rule.event}>
              {i ? <View style={styles.divider} /> : null}
              <Row style={styles.row}>
                <AppText style={styles.flex}>{rule.description}</AppText>
                {rule.points ? <Tag label={`+${rule.points}`} tone="gold" /> : null}
              </Row>
            </View>
          ))}
        </Card>
      </ScrollView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  member: { borderRadius: radius.xl, padding: spacing.lg, gap: spacing.xs, overflow: 'hidden', minHeight: 180, justifyContent: 'flex-end' },
  orb: { position: 'absolute', width: 240, height: 240, borderRadius: 120, backgroundColor: 'rgba(255,255,255,0.12)', top: -110, right: -70 },
  memberKicker: { color: 'rgba(255,255,255,0.85)', fontSize: 12, letterSpacing: 2, textTransform: 'uppercase', fontWeight: '600' },
  memberPoints: { color: colors.onPrimary, fontSize: 40, fontFamily: fonts.display, fontWeight: '700' },
  memberLine: { width: 44, height: 3, borderRadius: 2 },
  memberNote: { color: 'rgba(255,255,255,0.9)', fontSize: 14 },
  divider: { height: 1, backgroundColor: colors.border, marginVertical: spacing.sm },
  flex: { flex: 1 },
  content: { padding: spacing.lg, gap: spacing.md },
  row: { gap: spacing.sm },
});
