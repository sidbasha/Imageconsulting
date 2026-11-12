import React, { useState } from 'react';
import { ActivityIndicator, ScrollView, StyleSheet } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { useTranslation } from 'react-i18next';

import { AppText, Button, Card, Chips, ErrorBanner, Row, Screen, ScreenHeader, TextField, money } from '../components/ui';
import { useApp } from '../contexts/AppContext';
import type { AppStackParams } from '../navigation/RootNavigator';
import { colors, spacing } from '../theme';
import { errorMessage } from './errorMessage';
import { useLoad } from './useLoad';

type Props = NativeStackScreenProps<AppStackParams, 'StylistServices'>;
const KINDS = ['consultation', 'occasion_audit', 'wardrobe_audit', 'makeup_audit', 'expert_color', 'personal_shopper_day'];
const DATE = /^\d{4}-\d{2}-\d{2}$/;
const TIME = /^([01]\d|2[0-3]):[0-5]\d$/;

/** A stylist's services, prices and availability (rows 18, 19, 46). */
export function StylistServicesScreen({ navigation }: Props) {
  const { t, i18n } = useTranslation();
  const { api, features } = useApp();
  const services = useLoad(() => api.myServices(), [api]);
  const slots = useLoad(() => api.mySlots(), [api]);
  const on = new Set(features ?? []);
  const [kind, setKind] = useState<string | null>('consultation');
  const [title, setTitle] = useState('');
  const [price, setPrice] = useState('');
  const [minutes, setMinutes] = useState('30');
  const [date, setDate] = useState('');
  const [times, setTimes] = useState('10:00, 11:00');
  const [length, setLength] = useState('30');
  const [busy, setBusy] = useState<string | null>(null);
  const [failure, setFailure] = useState<unknown>(null);
  const [problem, setProblem] = useState<string | null>(null);

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

  const addService = () => {
    const amount = Number(price.replace(',', '.'));
    if (!kind || !title.trim() || !(amount >= 0) || !price.trim()) {
      setProblem(t('services_admin.fill'));
      return;
    }
    setProblem(null);
    const inPerson = kind === 'personal_shopper_day';
    return run('service', async () => {
      await api.addService({ kind, title: title.trim(), description: '', price_minor: Math.round(amount * 100),
        duration_minutes: Number(minutes) || 30, mode: inPerson ? 'in_person' : 'online' });
      setTitle('');
      setPrice('');
      await services.reload();
    });
  };

  const addSlots = () => {
    const list = times.split(',').map(s => s.trim()).filter(Boolean);
    if (!DATE.test(date.trim()) || !list.length || !list.every(x => TIME.test(x))) {
      setProblem(t('services_admin.badTimes'));
      return;
    }
    setProblem(null);
    // Times are entered in the device's own time zone and sent with its offset.
    const starts = list.map(x => new Date(`${date.trim()}T${x}:00`).toISOString());
    return run('slots', async () => {
      await api.addSlots(starts, Number(length) || 30);
      await slots.reload();
    });
  };

  const toggle = (s: NonNullable<typeof services.data>[number]) =>
    run(s.id, async () => {
      await api.updateService(s.id, { kind: s.kind, title: s.title, description: s.description, price_minor: s.price_minor,
        duration_minutes: s.duration_minutes, mode: s.mode, is_active: !s.is_active });
      await services.reload();
    });

  const when = (iso: string) =>
    new Date(iso).toLocaleString(i18n.language === 'ar' ? 'ar-AE' : 'en-AE', { weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });

  return (
    <Screen testID="stylist-services">
      <ScrollView contentContainerStyle={styles.content}>
        <ScreenHeader title={t('services_admin.title')} onBack={() => navigation.goBack()} />
        <ErrorBanner message={services.error ? errorMessage(services.error, t) : failure ? errorMessage(failure, t) : problem} />
        {services.loading && !services.data ? <ActivityIndicator color={colors.primary} /> : null}
        {services.data?.map(s => (
          <Card key={s.id}>
            <AppText variant="heading">{s.title}</AppText>
            <AppText muted>{`${t(`services.${s.kind}`)} · ${money(s.price_minor, s.currency)} · ${s.duration_minutes} min`}</AppText>
            <Button kind="link" label={s.is_active ? t('services_admin.pause') : t('services_admin.resume')}
              onPress={() => toggle(s)} loading={busy === s.id} testID={`toggle-${s.id}`} />
          </Card>
        ))}
        <Card>
          <AppText variant="heading">{t('services_admin.add')}</AppText>
          <Chips value={kind} onChange={setKind} testID="new-kind"
            options={KINDS.filter(k => on.has(SERVICE_FEATURES[k])).map(k => ({ value: k, label: t(`services.${k}`) }))} />
          <TextField label={t('services_admin.name')} value={title} onChangeText={setTitle} testID="service-title" />
          <TextField label={t('services_admin.price')} value={price} onChangeText={setPrice} keyboardType="decimal-pad" testID="service-price" />
          <TextField label={t('services_admin.minutes')} value={minutes} onChangeText={setMinutes} keyboardType="number-pad" testID="service-minutes" />
          <Button label={t('services_admin.save')} onPress={addService} loading={busy === 'service'} testID="add-service" />
        </Card>

        <AppText variant="heading">{t('services_admin.availability')}</AppText>
        {slots.data?.map(s => (
          <Row key={s.id} style={styles.row}>
            <AppText style={styles.flex}>{`${when(s.starts_at)}${s.booked ? ` · ${t('services_admin.booked')}` : ''}`}</AppText>
            {!s.booked ? (
              <Button kind="link" label={t('services_admin.remove')} testID={`remove-slot-${s.id}`}
                onPress={() => run(s.id, async () => { await api.deleteSlot(s.id); await slots.reload(); })} />
            ) : null}
          </Row>
        ))}
        <Card>
          <TextField label={t('services_admin.date')} hint="2026-12-01" value={date} onChangeText={setDate} testID="slot-date" />
          <TextField label={t('services_admin.times')} hint="10:00, 11:30, 14:00" value={times} onChangeText={setTimes} testID="slot-times" />
          <TextField label={t('services_admin.minutes')} value={length} onChangeText={setLength} keyboardType="number-pad" testID="slot-minutes" />
          <Button label={t('services_admin.addTimes')} onPress={addSlots} loading={busy === 'slots'} testID="add-slots" />
        </Card>
      </ScrollView>
    </Screen>
  );
}

const SERVICE_FEATURES: Record<string, string> = {
  consultation: 'phase2.consultations', occasion_audit: 'phase2.occasion_audit', wardrobe_audit: 'phase2.wardrobe_audit',
  makeup_audit: 'phase2.makeup_audit', expert_color: 'phase2.expert_color_analysis', personal_shopper_day: 'phase3.personal_shopper',
};

const styles = StyleSheet.create({
  flex: { flex: 1 },
  content: { padding: spacing.lg, gap: spacing.md },
  row: { gap: spacing.sm, alignItems: 'center' },
});
