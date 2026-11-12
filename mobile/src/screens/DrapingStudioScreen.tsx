import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { ActivityIndicator, Image, Pressable, ScrollView, StyleSheet, View } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { useTranslation } from 'react-i18next';

import type { DrapingAnswer, DrapingSession, DrapingStep } from '../api/client';
import { PaletteView } from '../components/PaletteView';
import { PhotoPicker } from '../components/PhotoThumb';
import { AppText, Button, Card, ErrorBanner, Row, Screen, ScreenHeader, TextField } from '../components/ui';
import { useApp } from '../contexts/AppContext';
import type { AppStackParams } from '../navigation/RootNavigator';
import { colors, gradients, radius, shadows, spacing } from '../theme';
import { errorMessage } from './errorMessage';
import { useLoad } from './useLoad';

/** What the studio needs from the API: the consultant's workspace or the customer's own photos. */
type StudioApi = {
  start: (photoId: string) => Promise<DrapingSession>;
  get: (sessionId: string) => Promise<DrapingSession>;
  answer: (sessionId: string, a: DrapingAnswer) => Promise<DrapingSession>;
  undo: (sessionId: string) => Promise<DrapingSession>;
  pair: (photoId: string, a: string, b: string) => Promise<string>;
  compare: (photoId: string, colours: string[]) => Promise<string>;
  // Consultant only:
  edit?: (sessionId: string, body: { custom_palette?: string[]; notes?: string }) => Promise<DrapingSession>;
  lips?: (photoId: string, colours: string[]) => Promise<string>;
};

/** Guided draping (consultant): on the client's shared face photo, inside the colour workspace. */
export function DrapingStudioScreen({ route, navigation }: NativeStackScreenProps<AppStackParams, 'DrapingStudio'>) {
  const { id, fileId, sessionId } = route.params;
  const { api } = useApp();
  const adapter = useMemo<StudioApi>(() => ({
    start: photo => api.startDraping(id, photo),
    get: sid => api.drapingSession(id, sid),
    answer: (sid, a) => api.answerDraping(id, sid, a),
    undo: sid => api.undoDraping(id, sid),
    pair: (photo, a, b) => api.drapePair(id, photo, a, b),
    compare: (photo, colours) => api.compareDrapes(id, photo, colours),
    edit: (sid, body) => api.editDraping(id, sid, body),
    lips: (photo, colours) => api.lipStudio(id, photo, colours),
  }), [api, id]);
  return <Studio adapter={adapter} photoId={fileId} sessionId={sessionId} onBack={() => navigation.goBack()}
    onReport={() => navigation.navigate('ReportEditor', { id })} />;
}

/** Guided draping (customer): the same steps on her own face photo; the result becomes her palette. */
export function SelfDrapingScreen({ route, navigation }: NativeStackScreenProps<AppStackParams, 'SelfDraping'>) {
  const { t } = useTranslation();
  const { api } = useApp();
  const photos = useLoad(() => api.photos(), [api]);
  const faces = (photos.data ?? []).filter(p => p.kind === 'face');
  const [chosen, setChosen] = useState<string | null>(route.params?.imageId ?? null);
  const [started, setStarted] = useState(!!route.params?.sessionId);
  const adapter = useMemo<StudioApi>(() => ({
    start: photo => api.startSelfDraping(photo),
    get: sid => api.selfDraping(sid),
    answer: (sid, a) => api.answerSelfDraping(sid, a),
    undo: sid => api.undoSelfDraping(sid),
    pair: (photo, a, b) => api.selfDrapePair(photo, a, b),
    compare: (photo, colours) => api.selfCompare(photo, colours),
  }), [api]);
  const photo = chosen ?? faces[0]?.id ?? null;
  if (started && (photo || route.params?.sessionId)) {
    return <Studio adapter={adapter} photoId={photo ?? ''} sessionId={route.params?.sessionId} onBack={() => navigation.goBack()}
      onSeePalette={() => navigation.replace('MyPalette')} />;
  }
  return (
    <Screen testID="self-draping-intro">
      <ScrollView contentContainerStyle={styles.content}>
        <ScreenHeader title={t('selfDraping.title')} onBack={() => navigation.goBack()} />
        <View style={[styles.intro, { backgroundImage: gradients.dusk }]}>
          <AppText style={styles.introTitle}>{t('selfDraping.heading')}</AppText>
          <AppText style={styles.introBody}>{t('selfDraping.explain')}</AppText>
        </View>
        <AppText variant="small" muted>{t('selfDraping.tips')}</AppText>
        {photos.loading && !photos.data ? <ActivityIndicator color={colors.primary} /> : null}
        {photos.data && faces.length === 0 ? (
          <Button label={t('analysis.addPhoto')} onPress={() => navigation.navigate('Photos')} testID="add-photo" />
        ) : null}
        {faces.length ? <PhotoPicker photos={faces} value={photo} onChange={setChosen} testID="self-photo" /> : null}
        {photo ? <Button label={t('selfDraping.start')} onPress={() => setStarted(true)} testID="self-start" /> : null}
      </ScrollView>
    </Screen>
  );
}

function Studio({ adapter, photoId, sessionId, onBack, onReport, onSeePalette }: {
  adapter: StudioApi; photoId: string; sessionId?: string; onBack: () => void; onReport?: () => void; onSeePalette?: () => void;
}) {
  const { t } = useTranslation();
  const consultant = !!adapter.edit;
  const [session, setSession] = useState<DrapingSession | null>(null);
  const [image, setImage] = useState<string | null>(null);
  const [imageKey, setImageKey] = useState<string | null>(null); // what the image shows, for highlighting
  const shownPair = useRef<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [failure, setFailure] = useState<unknown>(null);
  const [mine, setMine] = useState<string[]>([]);
  const [notes, setNotes] = useState('');
  const [lips, setLips] = useState<string[]>([]);
  const [lipImage, setLipImage] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  const act = useCallback(async (key: string, action: () => Promise<void>) => {
    setBusy(key);
    setFailure(null);
    try {
      await action();
    } catch (e) {
      setFailure(e);
    } finally {
      setBusy(null);
    }
  }, []);

  const adopt = (s: DrapingSession) => {
    setSession(s);
    setMine(s.custom_palette ?? []);
    setNotes(s.notes ?? '');
  };

  useEffect(() => {
    act('load', async () => adopt(sessionId ? await adapter.get(sessionId) : await adapter.start(photoId)));
  }, [act, adapter, photoId, sessionId]);

  const step = session?.next ?? null;
  const photo = session?.file_id ?? photoId;

  // The drape image for the comparison on screen; re-fetched only when the comparison changes.
  const pairKey = step && step.step !== 'confirm' ? `${step.pair.a}-${step.pair.b}` : null;
  useEffect(() => {
    if (!step || step.step === 'confirm' || !photo || !pairKey || pairKey === shownPair.current) {
      return;
    }
    let live = true;
    shownPair.current = pairKey;
    setImage(null);
    setImageKey(pairKey);
    adapter.pair(photo, step.pair.a, step.pair.b).then(u => live && setImage(u)).catch(e => {
      if (live) {
        shownPair.current = null; // allow a retry
        setFailure(e);
      }
    });
    return () => {
      live = false;
    };
  }, [adapter, photo, step, pairKey]);

  const answer = (a: DrapingAnswer) => session && act('answer', async () => adopt(await adapter.answer(session.id, a)));
  const undo = () => session && act('undo', async () => adopt(await adapter.undo(session.id)));
  const showType = (drapes: string[], key: string) =>
    photo && act(`show-${key}`, async () => {
      shownPair.current = null;
      setImageKey(key);
      setImage(await adapter.compare(photo, drapes));
    });

  const result = session?.result?.colour_type ?? null;
  const toggleMine = (hex: string) => {
    setSaved(false);
    setMine(list => (list.includes(hex) ? list.filter(x => x !== hex) : list.length >= 48 ? list : [...list, hex]));
  };
  const save = () => session && adapter.edit && act('save', async () => {
    adopt(await adapter.edit!(session.id, { custom_palette: mine, notes }));
    setSaved(true);
  });
  const toggleLip = (hex: string) => setLips(list => (list.includes(hex) ? list.filter(x => x !== hex) : list.length >= 6 ? list : [...list, hex]));

  return (
    <Screen testID={consultant ? 'draping-studio' : 'self-draping'}>
      <ScrollView contentContainerStyle={styles.content}>
        <ScreenHeader title={t(consultant ? 'studio.title' : 'selfDraping.title')} onBack={onBack} />
        {busy === 'load' && !session ? <ActivityIndicator color={colors.primary} /> : null}
        <ErrorBanner message={failure ? errorMessage(failure, t) : null} />

        {step ? <Progress step={step} /> : null}

        {step && step.step !== 'confirm' ? (
          <>
            <AppText variant="heading">{step.title}</AppText>
            <AppText muted>{step.prompt}</AppText>
            <View style={styles.stage}>
              {image ? (
                <Image source={{ uri: image }} style={styles.pair} resizeMode="contain" testID="drape-pair" />
              ) : (
                <ActivityIndicator color={colors.primary} style={styles.pair} />
              )}
              <Row style={styles.sides}>
                {(['a', 'b'] as const).map(side => (
                  <View key={side} style={styles.side}>
                    <View style={[styles.dot, { backgroundColor: step.pair[side] }]} />
                    <AppText variant="small" muted>{step.labels[side]}</AppText>
                  </View>
                ))}
              </Row>
            </View>
            <Row style={styles.choices}>
              <Choice label={t('studio.pickLeft', { side: step.labels.a })} onPress={() => answer({ step: step.step, pair: step.pair.index, pick: 'a' })}
                disabled={!!busy} testID="pick-a" />
              <Choice label={t('studio.same')} kind="soft" onPress={() => answer({ step: step.step, pair: step.pair.index, pick: 'same' })}
                disabled={!!busy} testID="pick-same" />
              <Choice label={t('studio.pickRight', { side: step.labels.b })} onPress={() => answer({ step: step.step, pair: step.pair.index, pick: 'b' })}
                disabled={!!busy} testID="pick-b" />
            </Row>
            {session && session.answers > 0 ? <Button kind="link" label={t('studio.undo')} onPress={undo} loading={busy === 'undo'} testID="undo" /> : null}
          </>
        ) : null}

        {step && step.step === 'confirm' ? (
          <>
            <AppText variant="heading">{step.title}</AppText>
            <AppText muted>{step.prompt}</AppText>
            {image ? <Image source={{ uri: image }} style={styles.grid} resizeMode="contain" testID="type-drapes" /> : null}
            {step.options.map(o => (
              <Card key={o.key} style={imageKey === o.key ? styles.optionOn : undefined}>
                <Row style={styles.optionHead}>
                  <AppText variant="heading" style={styles.flex}>{o.title}</AppText>
                  <AppText muted>{`${Math.round(o.score * 100)}%`}</AppText>
                </Row>
                <Row style={styles.sides}>
                  {o.drapes.map(hex => <View key={hex} style={[styles.drape, { backgroundColor: hex }]} />)}
                </Row>
                <Row style={styles.optionHead}>
                  <Button kind="soft" label={t('studio.showOnFace')} onPress={() => showType(o.drapes, o.key)} loading={busy === `show-${o.key}`}
                    testID={`show-${o.key}`} />
                  <Button label={t('studio.choose')} onPress={() => answer({ step: 'confirm', pick: o.key })} loading={busy === 'answer'}
                    testID={`choose-${o.key}`} />
                </Row>
              </Card>
            ))}
            <Button kind="link" label={t('studio.undo')} onPress={undo} loading={busy === 'undo'} testID="undo" />
          </>
        ) : null}

        {result && session ? (
          <>
            <View style={[styles.done, { backgroundImage: gradients.gold }]}>
              <AppText variant="small" style={styles.doneKicker}>{t('studio.result')}</AppText>
              <AppText variant="heading" style={styles.doneTitle} testID="studio-result">{result.title}</AppText>
              <AppText variant="small" style={styles.doneKicker}>
                {session.result!.scores.map(s => `${s.title} ${Math.round(s.score * 100)}%`).join(' · ')}
              </AppText>
            </View>

            {consultant ? <AppText variant="small" muted>{t('studio.customise')}</AppText> : null}
            <PaletteView type={result} selected={consultant ? mine : undefined} onToggle={consultant ? toggleMine : undefined} testID="studio-palette" />
            {onSeePalette ? (
              <>
                <AppText variant="small" muted>{t('selfDraping.indicative')}</AppText>
                <Button label={t('selfDraping.seePalette')} onPress={onSeePalette} testID="see-palette" />
              </>
            ) : null}
            {consultant ? (
            <>
            <Card>
              <AppText variant="heading">{t('studio.mine', { count: mine.length })}</AppText>
              <View style={styles.mine}>
                {mine.map(hex => <View key={hex} style={[styles.mineSwatch, { backgroundColor: hex }]} />)}
              </View>
              <TextField label={t('studio.notes')} value={notes} onChangeText={v => { setNotes(v); setSaved(false); }} multiline testID="studio-notes" />
              <Button label={saved ? t('studio.saved') : t('studio.save')} onPress={save} loading={busy === 'save'} testID="studio-save" />
            </Card>

            <Card>
              <AppText variant="heading">{t('studio.lipStudio')}</AppText>
              <AppText variant="small" muted>{t('studio.lipPick')}</AppText>
              <View style={styles.mine}>
                {result.lips.map(s => (
                  <Pressable key={s.hex} accessibilityRole="checkbox" accessibilityState={{ checked: lips.includes(s.hex) }} accessibilityLabel={s.name}
                    onPress={() => toggleLip(s.hex)} testID={`lip-${s.hex}`}
                    style={[styles.lip, { backgroundColor: s.hex }, lips.includes(s.hex) && styles.lipOn]} />
                ))}
              </View>
              <Button kind="soft" label={t('studio.compareLips')} loading={busy === 'lips'} testID="compare-lips"
                onPress={() => lips.length >= 2 && photo && adapter.lips && act('lips', async () => setLipImage(await adapter.lips!(photo, lips)))} />
              {lipImage ? <Image source={{ uri: lipImage }} style={styles.grid} resizeMode="contain" testID="lip-image" /> : null}
            </Card>

            </>
            ) : null}
            {onReport ? <Button label={t('workspace.writeReport')} onPress={onReport} testID="studio-report" /> : null}
            <Button kind="link" label={t('studio.redo')} onPress={undo} loading={busy === 'undo'} testID="reopen" />
          </>
        ) : null}
      </ScrollView>
    </Screen>
  );
}

function Progress({ step }: { step: DrapingStep }) {
  const { t } = useTranslation();
  const done = step.step === 'confirm' ? 1 : step.progress.answered / step.progress.total;
  return (
    <View style={styles.progress} testID="studio-progress">
      <AppText variant="small" muted>{t('studio.stepOf', { number: step.number, of: step.of, title: step.title })}</AppText>
      <Row style={styles.bars}>
        {Array.from({ length: step.of }, (_, i) => (
          <View key={i} style={styles.track}>
            <View style={[styles.fill, { width: `${i + 1 < step.number ? 100 : i + 1 === step.number ? Math.round(done * 100) : 0}%` }]} />
          </View>
        ))}
      </Row>
    </View>
  );
}

function Choice({ label, onPress, disabled, kind = 'primary', testID }: {
  label: string; onPress: () => void; disabled?: boolean; kind?: 'primary' | 'soft'; testID: string;
}) {
  return (
    <Pressable accessibilityRole="button" accessibilityLabel={label} onPress={onPress} disabled={disabled} testID={testID}
      style={({ pressed }) => [styles.choice, kind === 'primary' ? { backgroundImage: gradients.primary } : styles.choiceSoft,
        (pressed || disabled) && styles.pressed]}>
      <AppText style={kind === 'primary' ? styles.choiceLabel : styles.choiceLabelSoft}>{label}</AppText>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  intro: { borderRadius: radius.xl, padding: spacing.lg, gap: spacing.sm, boxShadow: shadows.lifted },
  introTitle: { color: '#FFFFFF', fontSize: 24, lineHeight: 32, fontWeight: '600' },
  introBody: { color: '#FFF1EC' },
  content: { padding: spacing.lg, gap: spacing.md, paddingBottom: spacing.xl * 2 },
  flex: { flex: 1 },
  progress: { gap: spacing.xs },
  bars: { gap: 6 },
  track: { flex: 1, height: 6, borderRadius: 3, backgroundColor: colors.primarySoft, overflow: 'hidden' },
  fill: { height: 6, backgroundColor: colors.primary },
  stage: { backgroundColor: colors.surface, borderRadius: radius.lg, padding: spacing.sm, gap: spacing.sm, boxShadow: shadows.soft },
  pair: { width: '100%', aspectRatio: 1.9, borderRadius: radius.md },
  grid: { width: '100%', aspectRatio: 1.6, borderRadius: radius.md, backgroundColor: colors.surface },
  sides: { justifyContent: 'space-around', gap: spacing.sm },
  side: { alignItems: 'center', gap: 4 },
  dot: { width: 28, height: 28, borderRadius: 14, borderWidth: 2, borderColor: colors.surface, boxShadow: shadows.soft },
  choices: { gap: spacing.sm },
  choice: { flex: 1, minHeight: 52, borderRadius: radius.pill, alignItems: 'center', justifyContent: 'center', paddingHorizontal: spacing.sm,
    boxShadow: shadows.button },
  choiceSoft: { backgroundColor: colors.primarySoft },
  choiceLabel: { color: colors.onPrimary, fontWeight: '600', textAlign: 'center' },
  choiceLabelSoft: { color: colors.primaryDeep, fontWeight: '600', textAlign: 'center' },
  pressed: { opacity: 0.7 },
  optionHead: { gap: spacing.sm, alignItems: 'center' },
  optionOn: { borderColor: colors.primary, borderWidth: 1.5 },
  drape: { flex: 1, height: 36, borderRadius: radius.sm },
  done: { borderRadius: radius.xl, padding: spacing.lg, gap: spacing.xs, boxShadow: shadows.lifted },
  doneKicker: { color: '#4A3520' },
  doneTitle: { color: '#2E1F12', fontSize: 26, lineHeight: 34 },
  mine: { flexDirection: 'row', flexWrap: 'wrap', gap: 6 },
  mineSwatch: { width: 28, height: 28, borderRadius: 6 },
  lip: { width: 44, height: 28, borderRadius: 14, borderWidth: 2, borderColor: 'transparent' },
  lipOn: { borderColor: colors.text },
});
