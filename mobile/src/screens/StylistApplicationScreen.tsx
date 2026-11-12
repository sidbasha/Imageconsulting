import React, { useEffect, useState } from 'react';
import { ActivityIndicator, ScrollView, StyleSheet } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { launchImageLibrary } from 'react-native-image-picker';
import { useTranslation } from 'react-i18next';

import { AppText, Button, Card, Chips, ErrorBanner, Screen, ScreenHeader, TextField } from '../components/ui';
import { useApp } from '../contexts/AppContext';
import type { AppStackParams } from '../navigation/RootNavigator';
import { colors, spacing } from '../theme';
import { errorMessage } from './errorMessage';
import { useLoad } from './useLoad';

type Props = NativeStackScreenProps<AppStackParams, 'StylistApplication'>;
const KINDS = ['certification', 'practice_evidence', 'invoice', 'testimonial', 'referral', 'business_license'];

/** Apply to offer services (rows 15, 16). Credentials are photographed; PDF upload needs a document picker (not added). */
export function StylistApplicationScreen({ navigation }: Props) {
  const { t } = useTranslation();
  const { api } = useApp();
  const application = useLoad(() => api.myApplication(), [api]);
  const credentials = useLoad(() => api.myApplication().then(a => (a ? api.credentials() : [])), [api]);
  const [bio, setBio] = useState('');
  const [city, setCity] = useState('');
  const [kind, setKind] = useState<string | null>('certification');
  const [title, setTitle] = useState('');
  const [busy, setBusy] = useState<string | null>(null);
  const [failure, setFailure] = useState<unknown>(null);

  useEffect(() => {
    if (application.data) {
      setBio(application.data.bio);
      setCity(application.data.city ?? '');
    }
  }, [application.data]);

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
  const save = () => run('save', async () => application.setData(await api.saveApplication({ bio, city, languages: ['en', 'ar'] })));
  const addCredential = () =>
    run('credential', async () => {
      if (!application.data) {
        application.setData(await api.saveApplication({ bio, city, languages: ['en', 'ar'] }));
      }
      const picked = await launchImageLibrary({ mediaType: 'photo', selectionLimit: 1, quality: 0.9 });
      const a = picked.assets?.[0];
      if (!a?.uri || !kind) {
        return;
      }
      await api.addCredential(kind, title || t(`application.kinds.${kind}`), { uri: a.uri, name: a.fileName ?? 'credential.jpg', type: a.type ?? 'image/jpeg' });
      setTitle('');
      await credentials.reload();
    });
  const submit = () => run('submit', async () => application.setData(await api.submitApplication()));

  const status = application.data?.status ?? 'draft';
  const editable = status === 'draft' || status === 'rejected';
  return (
    <Screen testID="stylist-application">
      <ScrollView contentContainerStyle={styles.content}>
        <ScreenHeader title={t('application.title')} onBack={() => navigation.goBack()} />
        {application.loading && !application.data ? <ActivityIndicator color={colors.primary} /> : null}
        <ErrorBanner message={application.error ? errorMessage(application.error, t) : failure ? errorMessage(failure, t) : null} />
        <Card>
          <AppText variant="heading" testID="application-status">{t(`application.status.${status}`)}</AppText>
          {application.data?.review_note ? <AppText muted>{application.data.review_note}</AppText> : null}
        </Card>
        {editable ? (
          <>
            <TextField label={t('application.bio')} value={bio} onChangeText={setBio} multiline testID="bio" />
            <TextField label={t('application.city')} value={city} onChangeText={setCity} testID="application-city" />
            <Button kind="link" label={t('application.save')} onPress={save} loading={busy === 'save'} testID="save-application" />
            <Card>
              <AppText variant="heading">{t('application.credentials')}</AppText>
              {(credentials.data ?? []).map(c => (
                <AppText key={c.id}>{`${c.title} · ${t(`application.credentialStatus.${c.status}`)}`}</AppText>
              ))}
              <Chips value={kind} onChange={setKind} testID="credential-kind"
                options={KINDS.map(k => ({ value: k, label: t(`application.kinds.${k}`) }))} />
              <TextField label={t('application.credentialTitle')} value={title} onChangeText={setTitle} testID="credential-title" />
              <Button kind="link" label={t('application.addCredential')} onPress={addCredential} loading={busy === 'credential'} testID="add-credential" />
            </Card>
            <Button label={t('application.submit')} onPress={submit} loading={busy === 'submit'} testID="submit-application" />
          </>
        ) : null}
        {status === 'approved' ? (
          <Button label={t('application.openPractice')} onPress={() => navigation.navigate('Practice')} testID="open-practice" />
        ) : null}
      </ScrollView>
    </Screen>
  );
}

const styles = StyleSheet.create({ content: { padding: spacing.lg, gap: spacing.md } });
