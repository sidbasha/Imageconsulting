import React, { useEffect, useState } from 'react';
import { ActivityIndicator, Linking, ScrollView, StyleSheet, View } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { launchImageLibrary } from 'react-native-image-picker';
import { useTranslation } from 'react-i18next';

import { AppText, Bullets, Button, Card, Chips, ErrorBanner, Palette, Screen, ScreenHeader, TextField } from '../components/ui';
import { useApp } from '../contexts/AppContext';
import type { AppStackParams } from '../navigation/RootNavigator';
import { colors, spacing } from '../theme';
import { errorMessage } from './errorMessage';
import { useLoad } from './useLoad';

type Props = NativeStackScreenProps<AppStackParams, 'Consultation'>;

/** A booked consultation or audit (rows 20-24): intake, photos for the stylist, and the delivered report (25). */
export function ConsultationScreen({ route, navigation }: Props) {
  const { id } = route.params;
  const { t } = useTranslation();
  const { api, language } = useApp();
  const { data, error, loading, setData } = useLoad(() => api.consultation(id), [api, id, language]);
  const photos = useLoad(() => api.photos().catch(() => []), [api]);
  const [intake, setIntake] = useState<Record<string, string>>({});
  const [purpose, setPurpose] = useState<string | null>(null);
  const [caption, setCaption] = useState('');
  const [busy, setBusy] = useState<string | null>(null);
  const [failure, setFailure] = useState<unknown>(null);

  useEffect(() => {
    if (data) {
      setIntake(data.intake);
      setPurpose(p => p ?? data.allowed_purposes[0] ?? null);
    }
  }, [data]);

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
  const refresh = async () => setData(await api.consultation(id));

  const addPhoto = () =>
    run('photo', async () => {
      const picked = await launchImageLibrary({ mediaType: 'photo', selectionLimit: 1, maxWidth: 2000, maxHeight: 2000, quality: 0.9 });
      const a = picked.assets?.[0];
      if (!a?.uri || !purpose) {
        return;
      }
      await api.addConsultationPhoto(id, { uri: a.uri, name: a.fileName ?? 'photo.jpg', type: a.type ?? 'image/jpeg' }, purpose, caption || undefined);
      setCaption('');
      await refresh();
    });

  const openReport = () =>
    run('report', async () => {
      const { path } = await api.reportLink(id);
      await Linking.openURL(api.absolute(path));
    });

  const fields = data ? [...new Set([...data.required_intake, ...(data.kind === 'consultation' ? ['notes'] : [])])] : [];

  return (
    <Screen testID="consultation">
      <ScrollView contentContainerStyle={styles.content}>
        <ScreenHeader title={data ? t(`services.${data.kind}`) : ''} onBack={() => navigation.goBack()} />
        {loading && !data ? <ActivityIndicator color={colors.primary} /> : null}
        <ErrorBanner message={error ? errorMessage(error, t) : failure ? errorMessage(failure, t) : null} />
        {data ? (
          <>
            <AppText muted>{t('consultation.with', { name: data.stylist.display_name })}</AppText>

            {data.report ? (
              <Card>
                <AppText variant="heading" testID="report-title">
                  {data.report.title}
                </AppText>
                {data.report.sections.map(s => (
                  <View key={s.key} style={styles.gap}>
                    <AppText variant="small" muted>
                      {s.title}
                    </AppText>
                    {s.type === 'list' ? <Bullets items={s.value} /> : s.type === 'palette' ? <Palette colors={s.value} />
                      : <AppText>{typeof s.value === 'object' ? s.value.label : s.value}</AppText>}
                  </View>
                ))}
                <Button kind="link" label={t('consultation.openPdf')} onPress={openReport} loading={busy === 'report'} testID="open-report" />
              </Card>
            ) : (
              <AppText muted>{t('consultation.reportPending')}</AppText>
            )}

            {fields.length ? (
              <Card>
                <AppText variant="heading">{t('consultation.aboutYou')}</AppText>
                {fields.map(f => (
                  <TextField key={f} label={t(`consultation.intake.${f}`)} value={intake[f] ?? ''} multiline testID={`intake-${f}`}
                    onChangeText={v => setIntake(i => ({ ...i, [f]: v }))} />
                ))}
                <Button label={t('consultation.saveIntake')} loading={busy === 'intake'} testID="save-intake"
                  onPress={() => run('intake', async () => setData(await api.saveIntake(id, intake)))} />
              </Card>
            ) : null}

            <Card>
              <AppText variant="heading">{t('consultation.photos')}</AppText>
              {data.files.map(f => (
                <AppText key={f.id}>
                  {`${t(`consultation.purpose.${f.purpose}`)}${f.caption ? `: ${f.caption}` : ''}${f.verdict ? ` · ${t(`consultation.verdict.${f.verdict.verdict}`)}` : ''}`}
                </AppText>
              ))}
              <Chips value={purpose} onChange={setPurpose} testID="purpose"
                options={data.allowed_purposes.map(p => ({ value: p, label: t(`consultation.purpose.${p}`) }))} />
              <TextField label={t('consultation.caption')} value={caption} onChangeText={setCaption} testID="caption" />
              <AppText variant="small" muted>
                {t('consultation.consent')}
              </AppText>
              <Button label={t('consultation.addPhoto')} onPress={addPhoto} loading={busy === 'photo'} testID="add-consultation-photo" />
              {(photos.data ?? []).filter(p => p.kind === 'face' && data.allowed_purposes.includes('face')).slice(0, 1).map(p => (
                <Button key={p.id} kind="link" label={t('consultation.shareMyPhoto')} testID="share-photo"
                  onPress={() => run('share', async () => { await api.sharePhoto(id, p.id); await refresh(); })} />
              ))}
            </Card>
          </>
        ) : null}
      </ScrollView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  content: { padding: spacing.lg, gap: spacing.md },
  gap: { gap: spacing.xs },
});
