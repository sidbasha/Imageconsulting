import React, { useEffect, useState } from 'react';
import { ActivityIndicator, ScrollView, StyleSheet } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { launchImageLibrary } from 'react-native-image-picker';
import { useTranslation } from 'react-i18next';

import type { Gender } from '../api/client';
import { AppText, Bullets, Button, Card, Chips, ErrorBanner, Screen, ScreenHeader, TextField } from '../components/ui';
import { useApp } from '../contexts/AppContext';
import type { AppStackParams } from '../navigation/RootNavigator';
import { colors, spacing } from '../theme';
import { errorMessage } from './errorMessage';
import { useLoad } from './useLoad';

type Props = NativeStackScreenProps<AppStackParams, 'Profile'>;
const DATE = /^\d{4}-\d{2}-\d{2}$/;

/** Eligibility facts (rows 2, 3) and identity verification (row 1). */
export function ProfileScreen({ navigation }: Props) {
  const { t } = useTranslation();
  const { api, language, features } = useApp();
  const profile = useLoad(() => api.profile(), [api]);
  const countries = useLoad(() => api.countries(), [api, language]);
  const [dob, setDob] = useState('');
  const [gender, setGender] = useState<Gender | null>(null);
  const [country, setCountry] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [failure, setFailure] = useState<unknown>(null);
  const [sent, setSent] = useState(false);
  const identityOn = (features ?? []).includes('phase1.identity_verification');

  useEffect(() => {
    if (profile.data) {
      setDob(profile.data.date_of_birth ?? '');
      setGender(profile.data.gender);
      setCountry(profile.data.country_code);
    }
  }, [profile.data]);

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

  const save = () =>
    run('save', async () => {
      profile.setData(await api.updateProfile({ date_of_birth: DATE.test(dob) ? dob : undefined, gender: gender ?? undefined, country_code: country ?? undefined }));
    });

  const uploadId = () =>
    run('id', async () => {
      const picked = await launchImageLibrary({ mediaType: 'photo', selectionLimit: 2, maxWidth: 2000, maxHeight: 2000, quality: 0.9 });
      const files = (picked.assets ?? []).filter(a => a.uri).map(a => ({ uri: a.uri!, name: a.fileName ?? 'id.jpg', type: a.type ?? 'image/jpeg' }));
      if (!files.length) {
        return;
      }
      await api.uploadIdDocument(files[0], files[1]);
      setSent(true);
      await profile.reload();
    });

  const p = profile.data;
  const locked = p?.identity_status === 'verified';
  return (
    <Screen testID="profile">
      <ScrollView contentContainerStyle={styles.content}>
        <ScreenHeader title={t('profile.title')} onBack={() => navigation.goBack()} />
        {profile.loading && !p ? <ActivityIndicator color={colors.primary} /> : null}
        <ErrorBanner message={profile.error ? errorMessage(profile.error, t) : failure ? errorMessage(failure, t) : null} />
        {p ? (
          <Card>
            <AppText variant="heading" testID="eligibility-status">
              {t(`profile.status.${p.eligibility_status}`)}
            </AppText>
            {p.eligibility_reasons.length ? (
              <Bullets items={p.eligibility_reasons.map(r => t(`profile.reasons.${r}`, { defaultValue: r }))} />
            ) : null}
          </Card>
        ) : null}
        <TextField label={t('profile.dob')} hint={t('profile.dobHint')} value={dob} onChangeText={setDob} editable={!locked}
          keyboardType="numbers-and-punctuation" testID="dob" />
        <Chips label={t('profile.gender')} value={gender} onChange={v => !locked && setGender(v)} testID="gender"
          options={[{ value: 'female', label: t('profile.female') }, { value: 'male', label: t('profile.male') }]} />
        <Chips label={t('profile.country')} value={country} onChange={setCountry} testID="country"
          options={(countries.data ?? []).map(c => ({ value: c.code, label: c.name }))} />
        <Button label={t('profile.save')} onPress={save} loading={busy === 'save'} testID="save-profile" />

        {identityOn && p ? (
          <Card>
            <AppText variant="heading">{t('identity.title')}</AppText>
            <AppText testID="identity-status">{t(`identity.status.${p.identity_status}`)}</AppText>
            {p.identity_status === 'unverified' || p.identity_status === 'rejected' ? (
              <>
                <AppText variant="small" muted>
                  {t('identity.explain')}
                </AppText>
                <Button label={t('identity.uploadId')} onPress={uploadId} loading={busy === 'id'} testID="upload-id" />
              </>
            ) : null}
            {sent ? <AppText testID="id-sent">{t('identity.sent')}</AppText> : null}
          </Card>
        ) : null}
      </ScrollView>
    </Screen>
  );
}

const styles = StyleSheet.create({ content: { padding: spacing.lg, gap: spacing.md } });
