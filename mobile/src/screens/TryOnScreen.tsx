import React, { useEffect, useState } from 'react';
import { ActivityIndicator, Image, Pressable, ScrollView, StyleSheet, View } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { useTranslation } from 'react-i18next';

import { ApiError, type TryOnItem } from '../api/client';
import { AppText, Bullets, Button, Chips, ErrorBanner, Row, Screen, ScreenHeader } from '../components/ui';
import { useApp } from '../contexts/AppContext';
import type { AppStackParams } from '../navigation/RootNavigator';
import { colors, radius, spacing } from '../theme';
import { errorMessage } from './errorMessage';
import { useLoad } from './useLoad';

type Props = NativeStackScreenProps<AppStackParams, 'TryOn'>;
const HAIR_COLOURS = ['#2b1b12', '#5a3825', '#8b2e1a', '#a0522d', '#c99a5b'];

/** Garments and hairstyles from the catalogue, fitted onto the user's own photo (rows 11, 12). */
export function TryOnScreen({ route, navigation }: Props) {
  const { kind } = route.params;
  const { t } = useTranslation();
  const { api, language } = useApp();
  const needs = kind === 'garment' ? 'full_body' : 'face';
  const items = useLoad(() => api.tryOnItems(kind), [api, kind, language]);
  const photos = useLoad(() => api.photos(), [api]);
  const usable = (photos.data ?? []).filter(p => p.kind === needs);
  const [photo, setPhoto] = useState<string | null>(null);
  const [item, setItem] = useState<string | null>(null);
  const [colour, setColour] = useState<string | null>(null);
  const [image, setImage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<unknown>(null);
  const chosenPhoto = photo ?? usable[0]?.id ?? null;

  const show = async () => {
    if (!chosenPhoto || !item) {
      return;
    }
    setBusy(true);
    setFailure(null);
    try {
      setImage(await api.tryOn(kind, chosenPhoto, item, colour ?? undefined));
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
    <Screen testID="try-on">
      <ScrollView contentContainerStyle={styles.content}>
        <ScreenHeader title={t(`tryOn.title.${kind}`)} onBack={() => navigation.goBack()} />
        <AppText muted>{t(`tryOn.intro.${kind}`)}</AppText>
        {photos.data && usable.length === 0 ? (
          <Button label={t('analysis.addPhoto')} onPress={() => navigation.navigate('Photos')} testID="add-photo" />
        ) : null}
        {usable.length > 1 ? (
          <Chips label={t('preview.photo')} value={chosenPhoto} onChange={setPhoto} testID="photo"
            options={usable.map((p, i) => ({ value: p.id, label: `${i + 1} · ${p.created_at.slice(0, 10)}` }))} />
        ) : null}
        {items.loading && !items.data ? <ActivityIndicator color={colors.primary} /> : null}
        {items.data && items.data.length === 0 ? <AppText muted>{t('tryOn.empty')}</AppText> : null}
        <Row style={styles.grid}>
          {items.data?.map(i => <ItemTile key={i.id} item={i} selected={i.id === item} onPress={() => setItem(i.id)} />)}
        </Row>
        {kind === 'hairstyle' ? (
          <>
            <AppText variant="small" muted>{t('tryOn.keepColour')}</AppText>
            <Row style={styles.grid}>
              {HAIR_COLOURS.map(c => (
                <Pressable key={c} accessibilityRole="radio" accessibilityState={{ selected: c === colour }} accessibilityLabel={c}
                  testID={`hair-${c}`} onPress={() => setColour(c === colour ? null : c)}
                  style={[styles.swatch, { backgroundColor: c }, c === colour && styles.swatchSelected]} />
              ))}
            </Row>
          </>
        ) : null}
        <Button label={t('preview.show')} onPress={show} loading={busy} testID="show-try-on" />
        {reasons ? <Bullets items={reasons.map(code => t(`analysis.reasons.${code}`, { defaultValue: code }))} />
          : <ErrorBanner message={items.error ? errorMessage(items.error, t) : failure ? errorMessage(failure, t) : null} />}
        {image ? (
          <View>
            <Image source={{ uri: image }} style={styles.result} resizeMode="contain" accessibilityLabel={t('preview.result')} testID="try-on-image" />
            <AppText variant="small" muted>{t(`tryOn.disclaimer.${kind}`)}</AppText>
          </View>
        ) : null}
      </ScrollView>
    </Screen>
  );
}

function ItemTile({ item, selected, onPress }: { item: TryOnItem; selected: boolean; onPress: () => void }) {
  const { api } = useApp();
  const { t } = useTranslation();
  const [uri, setUri] = useState<string | null>(null);
  useEffect(() => {
    let live = true;
    api.tryOnImage(item.id).then(u => live && setUri(u)).catch(() => undefined);
    return () => {
      live = false;
    };
  }, [api, item.id]);
  return (
    <Pressable accessibilityRole="radio" accessibilityState={{ selected }} accessibilityLabel={item.title}
      testID={`item-${item.id}`} onPress={onPress} style={[styles.tile, selected && styles.tileSelected]}>
      {uri ? <Image source={{ uri }} style={styles.thumb} resizeMode="contain" /> : <View style={styles.thumb} />}
      <AppText variant="small">{item.title}</AppText>
      {item.suggested ? <AppText variant="small" muted>{t('tryOn.suggested')}</AppText> : null}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  content: { padding: spacing.lg, gap: spacing.md },
  grid: { gap: spacing.sm, flexWrap: 'wrap' },
  tile: { width: 104, padding: spacing.xs, borderRadius: radius.md, borderWidth: 1, borderColor: colors.border, backgroundColor: colors.surface },
  tileSelected: { borderColor: colors.primary, borderWidth: 2 },
  thumb: { width: '100%', height: 110 },
  swatch: { width: 40, height: 40, borderRadius: 20, borderWidth: 2, borderColor: colors.border },
  swatchSelected: { borderColor: colors.text, borderWidth: 3 },
  result: { width: '100%', aspectRatio: 3 / 4, borderRadius: radius.md, backgroundColor: colors.surface },
});
