import React, { useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, View } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { launchCamera, launchImageLibrary, type ImagePickerResponse } from 'react-native-image-picker';
import { useTranslation } from 'react-i18next';

import { ApiError, type PhotoKind } from '../api/client';
import { AppText, Bullets, Button, Card, ErrorBanner, Row, Screen, ScreenHeader } from '../components/ui';
import { useApp } from '../contexts/AppContext';
import type { AppStackParams } from '../navigation/RootNavigator';
import { colors, radius, spacing } from '../theme';
import { errorMessage } from './errorMessage';
import { useLoad } from './useLoad';

type Props = NativeStackScreenProps<AppStackParams, 'Photos'>;

const KINDS: PhotoKind[] = ['face', 'full_body'];
// Downscale on the device: plenty for assessment, and keeps uploads well under the 10 MB limit.
const PICKER = { mediaType: 'photo', selectionLimit: 1, maxWidth: 2000, maxHeight: 2000, quality: 0.9 } as const;

export function PhotosScreen({ navigation }: Props) {
  const { t } = useTranslation();
  const { api } = useApp();
  const { data: photos, error, loading, reload } = useLoad(() => api.photos(), [api]);
  const [kind, setKind] = useState<PhotoKind>('face');
  const [consent, setConsent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<unknown>(null);
  const [needConsent, setNeedConsent] = useState(false);
  const [added, setAdded] = useState(false);

  const add = async (pick: (options: typeof PICKER) => Promise<ImagePickerResponse>) => {
    setAdded(false);
    setFailure(null);
    if (!consent) {
      setNeedConsent(true); // nothing is picked, let alone sent, without consent
      return;
    }
    const picked = await pick(PICKER);
    const asset = picked.assets?.[0];
    if (picked.didCancel || !asset?.uri) {
      return;
    }
    setBusy(true);
    try {
      await api.uploadPhoto(
        { uri: asset.uri, name: asset.fileName ?? 'photo.jpg', type: asset.type ?? 'image/jpeg' },
        kind,
        consent,
      );
      setAdded(true);
      await reload();
    } catch (e) {
      setFailure(e);
    } finally {
      setBusy(false);
    }
  };

  const remove = async (id: string) => {
    setFailure(null);
    try {
      await api.deletePhoto(id);
      await reload();
    } catch (e) {
      setFailure(e);
    }
  };

  // A rejected photo comes back with reason codes; each maps to a tip in the user's language.
  const reasons =
    failure instanceof ApiError && failure.code === 'photo_rejected'
      ? ((failure.detail as { reasons?: string[] })?.reasons ?? [])
      : null;

  return (
    <Screen testID="photos">
      <ScrollView contentContainerStyle={styles.content}>
        <ScreenHeader title={t('photos.title')} onBack={() => navigation.goBack()} />
        <AppText muted>{t('photos.intro')}</AppText>
        <AppText variant="small" muted>
          {t('photos.note')}
        </AppText>

        <Row style={styles.gapRow}>
          {KINDS.map(option => (
            <Pressable
              key={option}
              accessibilityRole="radio"
              accessibilityState={{ selected: option === kind }}
              testID={`kind-${option}`}
              onPress={() => setKind(option)}
              style={[styles.chip, option === kind && styles.chipSelected]}>
              <AppText variant="small" style={option === kind ? styles.chipLabelSelected : undefined}>
                {t(`photos.kind.${option}`)}
              </AppText>
            </Pressable>
          ))}
        </Row>

        <Pressable
          accessibilityRole="checkbox"
          accessibilityState={{ checked: consent }}
          accessibilityLabel={t('photos.consent')}
          testID="consent"
          onPress={() => {
            setConsent(!consent);
            setNeedConsent(false);
          }}>
          <Row style={styles.consent}>
            <View style={[styles.box, consent && styles.boxChecked]}>
              {consent ? <AppText style={styles.tick}>✓</AppText> : null}
            </View>
            <AppText style={styles.flex}>{t('photos.consent')}</AppText>
          </Row>
        </Pressable>
        <ErrorBanner message={needConsent ? t('photos.consentRequired') : null} />

        {reasons ? (
          <Card style={styles.rejected}>
            <AppText>{t('photos.rejected')}</AppText>
            <Bullets items={reasons.map(code => t(`photos.reasons.${code}`, { defaultValue: code }))} />
          </Card>
        ) : (
          <ErrorBanner message={failure ? errorMessage(failure, t) : null} />
        )}
        {added ? <AppText testID="added">{t('photos.uploaded')}</AppText> : null}

        <Button label={t('photos.choose')} onPress={() => add(launchImageLibrary)} loading={busy} testID="choose" />
        <Button kind="link" label={t('photos.take')} onPress={() => add(launchCamera)} testID="take" />

        {loading && !photos ? <ActivityIndicator color={colors.primary} accessibilityLabel={t('common.loading')} /> : null}
        {error ? <ErrorBanner message={errorMessage(error, t)} /> : null}
        {photos && photos.length === 0 ? <AppText muted>{t('photos.none')}</AppText> : null}
        {photos?.map(photo => (
          <Card key={photo.id}>
            <Row style={styles.gapRow}>
              <View style={styles.flex}>
                <AppText>{t(`photos.kind.${photo.kind}`)}</AppText>
                <AppText variant="small" muted>
                  {`${photo.width} × ${photo.height} · ${photo.created_at.slice(0, 10)}`}
                </AppText>
              </View>
              <Button kind="link" label={t('photos.delete')} onPress={() => remove(photo.id)} testID={`delete-${photo.id}`} />
            </Row>
          </Card>
        ))}
      </ScrollView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  content: { padding: spacing.lg, gap: spacing.md },
  gapRow: { gap: spacing.sm },
  chip: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 999,
    paddingHorizontal: spacing.md,
    minHeight: 40,
    justifyContent: 'center',
    backgroundColor: colors.surface,
  },
  chipSelected: { backgroundColor: colors.primary, borderColor: colors.primary },
  chipLabelSelected: { color: colors.onPrimary, fontWeight: '600' },
  consent: { gap: spacing.md, alignItems: 'flex-start' },
  box: {
    width: 24,
    height: 24,
    borderRadius: radius.md / 2,
    borderWidth: 2,
    borderColor: colors.primary,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.surface,
  },
  boxChecked: { backgroundColor: colors.primary },
  tick: { color: colors.onPrimary, fontSize: 14, lineHeight: 18, textAlign: 'center' },
  rejected: { borderColor: colors.danger },
});
