import React, { useState } from 'react';
import { ActivityIndicator, ScrollView, StyleSheet, View } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { useTranslation } from 'react-i18next';

import { ApiError, type AnalysisKind, type PhotoAnalysis } from '../api/client';
import { PhotoThumb } from '../components/PhotoThumb';
import { AppText, Bullets, Button, Card, ErrorBanner, Palette, Row, Screen, ScreenHeader, Tag } from '../components/ui';
import { useApp } from '../contexts/AppContext';
import type { AppStackParams } from '../navigation/RootNavigator';
import { colors, radius, spacing } from '../theme';
import { errorMessage } from './errorMessage';
import { useLoad } from './useLoad';

type Props = NativeStackScreenProps<AppStackParams, 'PhotoAnalysis'>;

const NEEDS: Record<AnalysisKind, 'face' | 'full_body'> = { face_shape: 'face', seasonal_color: 'face', body_shape: 'full_body' };

/** Runs an automated analysis on one of the user's photos and shows the indicative result. */
export function PhotoAnalysisScreen({ route, navigation }: Props) {
  const { kind } = route.params;
  const { t } = useTranslation();
  const { api, language } = useApp();
  const photos = useLoad(() => api.photos(), [api]);
  const previous = useLoad(() => api.latestAnalysis(kind), [api, kind, language]);
  const [result, setResult] = useState<PhotoAnalysis | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [failure, setFailure] = useState<unknown>(null);

  const usable = (photos.data ?? []).filter(p => p.kind === NEEDS[kind]);
  // A fresh result wins; otherwise the last saved one, clearly labelled as earlier.
  const shown = result ?? previous.data ?? null;
  const isPrevious = !result && !!shown;

  const run = async (imageId: string) => {
    setBusy(imageId);
    setFailure(null);
    try {
      setResult(await api.analysePhoto(kind, imageId));
    } catch (e) {
      setFailure(e);
    } finally {
      setBusy(null);
    }
  };

  const reasons =
    failure instanceof ApiError && failure.code === 'photo_not_analysable'
      ? ((failure.detail as { reasons?: string[] })?.reasons ?? [])
      : null;

  return (
    <Screen testID="photo-analysis">
      <ScrollView contentContainerStyle={styles.content}>
        <ScreenHeader title={t(`analysis.title.${kind}`)} onBack={() => navigation.goBack()} />
        <AppText muted>{t('analysis.intro')}</AppText>
        <AppText variant="small" muted>
          {t(`analysis.tips.${NEEDS[kind]}`)}
        </AppText>

        {photos.loading && !photos.data ? <ActivityIndicator color={colors.primary} accessibilityLabel={t('common.loading')} /> : null}
        {photos.data && usable.length === 0 ? (
          <View style={styles.gap}>
            <AppText>{t(`analysis.needPhoto.${NEEDS[kind]}`)}</AppText>
            <Button label={t('analysis.addPhoto')} onPress={() => navigation.navigate('Photos')} testID="add-photo" />
          </View>
        ) : null}
        {usable.map(photo => {
          const used = shown?.image_id === photo.id;
          return (
            <Card key={photo.id} style={used ? styles.used : undefined}>
              <Row style={styles.photoRow}>
                <PhotoThumb id={photo.id} testID={`photo-${photo.id}`} />
                <View style={[styles.flex, styles.gap]}>
                  <AppText>{t(`photos.kind.${photo.kind}`)}</AppText>
                  <AppText variant="small" muted>{photo.created_at.slice(0, 10)}</AppText>
                  {used ? <Tag label={t('analysis.analysed')} /> : null}
                  <Button label={t('analysis.run')} onPress={() => run(photo.id)} loading={busy === photo.id} testID={`analyse-${photo.id}`} />
                </View>
              </Row>
            </Card>
          );
        })}

        {reasons ? (
          <Card style={styles.problem}>
            <AppText>{t('analysis.notAnalysable')}</AppText>
            <Bullets items={reasons.map(code => t(`analysis.reasons.${code}`, { defaultValue: code }))} />
          </Card>
        ) : (
          <ErrorBanner message={failure ? errorMessage(failure, t) : null} />
        )}

        {shown?.profile ? (
          <Card>
            <AppText variant="heading" testID={isPrevious ? 'previous-result' : 'new-result'}>
              {isPrevious ? t('analysis.previous', { date: shown.created_at.slice(0, 10) }) : t('analysis.latest')}
            </AppText>
            {isPrevious ? <AppText variant="small" muted>{t('analysis.previousNote')}</AppText> : null}
            {shown.image_id ? (
              <Row style={styles.photoRow}>
                <PhotoThumb id={shown.image_id} style={styles.resultPhoto} />
                <AppText variant="small" muted style={styles.flex}>{t('analysis.fromPhoto')}</AppText>
              </Row>
            ) : null}
            <AppText variant="small" muted testID="indicative">
              {t('analysis.indicative')}
            </AppText>
            <AppText variant="heading" testID="analysis-result">
              {shown.profile.title}
            </AppText>
            <AppText>{shown.profile.summary}</AppText>
            {shown.low_confidence ? (
              <AppText variant="small" muted testID="low-confidence">
                {t('analysis.lowConfidence')}
              </AppText>
            ) : null}
            {shown.swatches ? (
              <View style={styles.gap}>
                <AppText variant="small" muted>
                  {t('analysis.sampled')}
                </AppText>
                <Palette colors={Object.values(shown.swatches)} />
              </View>
            ) : null}
            {shown.profile.palette ? <Palette colors={shown.profile.palette} /> : null}
            <AppText variant="small" muted>
              {t('analysis.closeness')}
            </AppText>
            {shown.scores.map(s => (
              <Row key={s.key} style={styles.gap}>
                <AppText style={styles.flex}>{s.title}</AppText>
                <AppText>{`${Math.round(s.score * 100)}%`}</AppText>
              </Row>
            ))}
            {Object.entries(shown.profile.advice).map(([category, items]) => (
              <View key={category} style={styles.gap}>
                <AppText variant="heading">{t(`analysis.advice.${category}`, { defaultValue: category })}</AppText>
                <Bullets items={items} />
              </View>
            ))}
          </Card>
        ) : null}
      </ScrollView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  content: { padding: spacing.lg, gap: spacing.md },
  gap: { gap: spacing.sm },
  problem: { borderColor: colors.danger },
  photoRow: { gap: spacing.md, alignItems: 'center' },
  used: { borderColor: colors.primary, borderWidth: 1.5, borderRadius: radius.lg },
  resultPhoto: { width: 56, height: 72 },
});
