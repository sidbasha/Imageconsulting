import React, { useState } from 'react';
import { ActivityIndicator, Image, Pressable, ScrollView, StyleSheet, View } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { useTranslation } from 'react-i18next';

import { ApiError, type PreviewKind } from '../api/client';
import { AppText, Bullets, Button, Chips, ErrorBanner, Row, Screen, ScreenHeader } from '../components/ui';
import { useApp } from '../contexts/AppContext';
import type { AppStackParams } from '../navigation/RootNavigator';
import { colors, radius, spacing } from '../theme';
import { errorMessage } from './errorMessage';
import { useLoad } from './useLoad';

type Props = NativeStackScreenProps<AppStackParams, 'Preview'>;

// Starting colours. The user's own season's palette is offered first when she has one.
const PRESETS: Record<PreviewKind, string[]> = {
  'hair-colour': ['#2b1b12', '#5a3825', '#8b2e1a', '#a0522d', '#c99a5b', '#e3c08d'],
  'outfit-colour': ['#1f3a93', '#2e6b4f', '#8e3b2c', '#c76b8e', '#f1c40f', '#2c2c2c'],
  makeup: ['#b0233a', '#c2185b', '#e8735a', '#a8452f', '#c76b8e', '#8b0a32'],
};
const BROWS = ['#2b1b12', '#4a3426', '#6b4a35', '#8a6a4f'];
const NEEDS: Record<PreviewKind, 'face' | 'full_body'> = { 'hair-colour': 'face', makeup: 'face', 'outfit-colour': 'full_body' };

export function PreviewScreen({ route, navigation }: Props) {
  const { kind } = route.params;
  const { t } = useTranslation();
  const { api } = useApp();
  const photos = useLoad(() => api.photos(), [api]);
  const season = useLoad(() => api.latestAnalysis('seasonal_color').catch(() => null), [api]);
  const usable = (photos.data ?? []).filter(p => p.kind === NEEDS[kind]);
  const [photo, setPhoto] = useState<string | null>(null);
  const [colour, setColour] = useState<string | null>(null);
  const [brow, setBrow] = useState<string | null>(null);
  const [image, setImage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<unknown>(null);

  const chosenPhoto = photo ?? usable[0]?.id ?? null;
  const palette = [...(kind === 'outfit-colour' ? season.data?.profile?.palette ?? [] : []), ...PRESETS[kind]];

  const show = async () => {
    if (!chosenPhoto || (!colour && !brow)) {
      return;
    }
    setBusy(true);
    setFailure(null);
    try {
      const body: Record<string, unknown> =
        kind === 'makeup'
          ? { image_id: chosenPhoto, lip_colour: colour ?? undefined, brow_colour: brow ?? undefined }
          : { image_id: chosenPhoto, colour };
      setImage(await api.preview(kind, body));
    } catch (e) {
      setFailure(e);
    } finally {
      setBusy(false);
    }
  };

  const reasons =
    failure instanceof ApiError && failure.code === 'photo_not_analysable'
      ? ((failure.detail as { reasons?: string[] })?.reasons ?? [])
      : null;

  return (
    <Screen testID="preview">
      <ScrollView contentContainerStyle={styles.content}>
        <ScreenHeader title={t(`preview.title.${kind}`)} onBack={() => navigation.goBack()} />
        <AppText muted>{t(`preview.intro.${kind}`)}</AppText>
        {photos.loading && !photos.data ? <ActivityIndicator color={colors.primary} /> : null}
        {photos.data && usable.length === 0 ? (
          <Button label={t('analysis.addPhoto')} onPress={() => navigation.navigate('Photos')} testID="add-photo" />
        ) : null}
        {usable.length > 1 ? (
          <Chips
            label={t('preview.photo')}
            value={chosenPhoto}
            onChange={setPhoto}
            options={usable.map((p, i) => ({ value: p.id, label: `${i + 1} · ${p.created_at.slice(0, 10)}` }))}
            testID="photo"
          />
        ) : null}
        <AppText variant="small" muted>
          {t(kind === 'makeup' ? 'preview.lipColour' : 'preview.colour')}
        </AppText>
        <ColourPicker colours={palette} value={colour} onChange={setColour} testID="colour" />
        {kind === 'makeup' ? (
          <>
            <AppText variant="small" muted>
              {t('preview.browColour')}
            </AppText>
            <ColourPicker colours={BROWS} value={brow} onChange={setBrow} testID="brow" />
          </>
        ) : null}
        <Button label={t('preview.show')} onPress={show} loading={busy} testID="show-preview" />
        {reasons ? (
          <Bullets items={reasons.map(code => t(`analysis.reasons.${code}`, { defaultValue: code }))} />
        ) : (
          <ErrorBanner message={failure ? errorMessage(failure, t) : null} />
        )}
        {image ? (
          <View>
            <Image source={{ uri: image }} style={styles.image} resizeMode="contain" accessibilityLabel={t('preview.result')} testID="preview-image" />
            <AppText variant="small" muted>
              {t(`preview.disclaimer.${kind}`)}
            </AppText>
          </View>
        ) : null}
      </ScrollView>
    </Screen>
  );
}

function ColourPicker({ colours, value, onChange, testID }: { colours: string[]; value: string | null; onChange: (c: string) => void; testID: string }) {
  return (
    <Row style={styles.swatches}>
      {[...new Set(colours)].map(c => (
        <Pressable
          key={c}
          accessibilityRole="radio"
          accessibilityState={{ selected: c === value }}
          accessibilityLabel={c}
          testID={`${testID}-${c}`}
          onPress={() => onChange(c)}
          style={[styles.swatch, { backgroundColor: c }, c === value && styles.swatchSelected]}
        />
      ))}
    </Row>
  );
}

const styles = StyleSheet.create({
  content: { padding: spacing.lg, gap: spacing.md },
  swatches: { gap: spacing.sm, flexWrap: 'wrap' },
  swatch: { width: 44, height: 44, borderRadius: 22, borderWidth: 2, borderColor: colors.border },
  swatchSelected: { borderColor: colors.text, borderWidth: 3 },
  image: { width: '100%', aspectRatio: 3 / 4, borderRadius: radius.md, backgroundColor: colors.surface },
});
