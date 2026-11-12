import React, { useState } from 'react';
import { ActivityIndicator, ScrollView, StyleSheet } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { useTranslation } from 'react-i18next';

import { AppText, Button, Card, ErrorBanner, Row, Screen, ScreenHeader, money } from '../components/ui';
import { useApp } from '../contexts/AppContext';
import type { AppStackParams } from '../navigation/RootNavigator';
import { colors, spacing } from '../theme';
import { errorMessage } from './errorMessage';
import { useLoad } from './useLoad';

/** A stylist's hub: bookings, with each one's report and colour workspace, services and availability, promotion. */
export function PracticeScreen({ navigation }: NativeStackScreenProps<AppStackParams, 'Practice'>) {
  const { t } = useTranslation();
  const { api, language, features } = useApp();
  const { data, error, loading, reload } = useLoad(() => api.practiceBookings(), [api, language]);
  const consultations = useLoad(() => api.consultations().catch(() => []), [api, language]);
  const on = new Set(features ?? []);
  const [failure, setFailure] = useState<unknown>(null);
  const complete = async (id: string) => {
    setFailure(null);
    try {
      await api.completeBooking(id);
      await reload();
    } catch (e) {
      setFailure(e);
    }
  };
  return (
    <Screen testID="practice">
      <ScrollView contentContainerStyle={styles.content}>
        <ScreenHeader title={t('practice.title')} onBack={() => navigation.goBack()} />
        <Button kind="link" label={t('practice.membership')} onPress={() => navigation.navigate('Plans', { audience: 'consultant' })} testID="membership" />
        <Button kind="link" label={t('practice.services')} onPress={() => navigation.navigate('StylistServices')} testID="open-services" />
        {on.has('phase2.paid_promotion') ? (
          <Button kind="link" label={t('practice.featured')} onPress={() => navigation.navigate('Featured')} testID="open-featured" />
        ) : null}
        {loading && !data ? <ActivityIndicator color={colors.primary} /> : null}
        <ErrorBanner message={error ? errorMessage(error, t) : failure ? errorMessage(failure, t) : null} />
        {data && data.length === 0 ? <AppText muted>{t('practice.none')}</AppText> : null}
        {data?.map(b => (
          <Card key={b.id}>
            <AppText variant="heading">{b.service.title}</AppText>
            <AppText muted>{`${b.starts_at.slice(0, 16).replace('T', ' ')} · ${money(b.price_minor, b.currency)} · ${t(`booking.status.${b.status}`, { defaultValue: b.status })}`}</AppText>
            <Row style={styles.row}>
              {(() => {
                const c = consultations.data?.find(x => x.booking_id === b.id);
                return c ? (
                  <>
                    {on.has('phase2.expert_reports') ? (
                      <Button kind="link" label={t('practice.report')} onPress={() => navigation.navigate('ReportEditor', { id: c.id })} testID={`report-${b.id}`} />
                    ) : null}
                    {on.has('phase2.color_workspace') ? (
                      <Button kind="link" label={t('practice.workspace')} onPress={() => navigation.navigate('Workspace', { id: c.id })} testID={`workspace-${b.id}`} />
                    ) : null}
                  </>
                ) : null;
              })()}
              {b.status === 'confirmed' ? <Button kind="link" label={t('practice.complete')} onPress={() => complete(b.id)} testID={`complete-${b.id}`} /> : null}
            </Row>
          </Card>
        ))}
      </ScrollView>
    </Screen>
  );
}

const styles = StyleSheet.create({ content: { padding: spacing.lg, gap: spacing.md }, row: { gap: spacing.md, flexWrap: 'wrap' } });
