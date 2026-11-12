import React, { useEffect, useState } from 'react';
import { ActivityIndicator, Image, Pressable, ScrollView, StyleSheet, View } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { useTranslation } from 'react-i18next';

import { ApiError, type Indicative } from '../api/client';
import { AppText, Button, Card, Chips, ErrorBanner, Palette, Row, Screen, ScreenHeader } from '../components/ui';
import { useApp } from '../contexts/AppContext';
import type { AppStackParams } from '../navigation/RootNavigator';
import { colors, radius, spacing } from '../theme';
import { errorMessage } from './errorMessage';
import { useLoad } from './useLoad';

type Props = NativeStackScreenProps<AppStackParams, 'Workspace'>;

// A drape set covering the four seasons; the consultant compares them against the face.
const DRAPES = ['#f4a582', '#e8735a', '#7fb3a3', '#c76b8e', '#9db4d4', '#8e3b2c', '#6b7d3a', '#1f3a93', '#a3123a', '#2c2c2c', '#f5f5f5', '#c99a5b'];

/** Consultant-only colour workspace (rows 27-29): drapes and an automated reading on the client's shared face photo. */
export function WorkspaceScreen({ route, navigation }: Props) {
  const { id } = route.params;
  const { t } = useTranslation();
  const { api, features } = useApp();
  const consultation = useLoad(() => api.consultation(id), [api, id]);
  const faces = (consultation.data?.files ?? []).filter(f => f.purpose === 'face');
  const [file, setFile] = useState<string | null>(null);
  const [opened, setOpened] = useState<{ credits_used: number } | null>(null);
  const [chosen, setChosen] = useState<string[]>([]);
  const [image, setImage] = useState<string | null>(null);
  const [reading, setReading] = useState<Indicative | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [failure, setFailure] = useState<unknown>(null);
  const chosenFile = file ?? faces[0]?.id ?? null;
  const draping = (features ?? []).includes('phase2.digital_draping');

  useEffect(() => {
    setImage(null);
  }, [chosenFile]);

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
  const toggleColour = (c: string) => setChosen(list => (list.includes(c) ? list.filter(x => x !== c) : list.length >= 8 ? list : [...list, c]));
  const needCredits = failure instanceof ApiError && failure.code === 'insufficient_credits';

  return (
    <Screen testID="workspace">
      <ScrollView contentContainerStyle={styles.content}>
        <ScreenHeader title={t('workspace.title')} onBack={() => navigation.goBack()} />
        {consultation.loading && !consultation.data ? <ActivityIndicator color={colors.primary} /> : null}
        <ErrorBanner message={consultation.error ? errorMessage(consultation.error, t) : failure ? errorMessage(failure, t) : null} />
        {needCredits ? (
          <Button kind="link" label={t('workspace.buyCredits')} onPress={() => navigation.navigate('Library', { kind: 'workspace_credits' })} testID="buy-credits" />
        ) : null}
        {consultation.data && faces.length === 0 ? <AppText muted>{t('workspace.noPhoto')}</AppText> : null}
        {faces.length && !opened ? (
          <Card>
            <AppText>{t('workspace.openExplain')}</AppText>
            <Button label={t('workspace.open')} loading={busy === 'open'} testID="open-workspace"
              onPress={() => run('open', async () => setOpened(await api.openWorkspace(id)))} />
          </Card>
        ) : null}
        {opened ? (
          <>
            <AppText variant="small" muted testID="credits-used">{t('workspace.credits', { count: opened.credits_used })}</AppText>
            {faces.length > 1 ? (
              <Chips value={chosenFile} onChange={setFile} testID="face" options={faces.map((f, i) => ({ value: f.id, label: `${i + 1}` }))} />
            ) : null}
            {draping ? (
              <>
                <AppText variant="small" muted>{t('workspace.pick')}</AppText>
                <Row style={styles.grid}>
                  {DRAPES.map(c => (
                    <Pressable key={c} accessibilityRole="checkbox" accessibilityState={{ checked: chosen.includes(c) }} accessibilityLabel={c}
                      testID={`drape-${c}`} onPress={() => toggleColour(c)}
                      style={[styles.swatch, { backgroundColor: c }, chosen.includes(c) && styles.swatchSelected]} />
                  ))}
                </Row>
                <Row style={styles.grid}>
                  <Button kind="link" label={t('workspace.drapeOne')} loading={busy === 'drape'} testID="drape-one"
                    onPress={() => chosen[0] && chosenFile && run('drape', async () => setImage(await api.drape(id, chosenFile, chosen[0])))} />
                  <Button kind="link" label={t('workspace.compare')} loading={busy === 'compare'} testID="compare"
                    onPress={() => chosen.length >= 2 && chosenFile && run('compare', async () => setImage(await api.compareDrapes(id, chosenFile, chosen)))} />
                </Row>
              </>
            ) : null}
            <Button kind="link" label={t('workspace.reading')} loading={busy === 'reading'} testID="indicative"
              onPress={() => chosenFile && run('reading', async () => setReading(await api.indicativeColour(id, chosenFile)))} />
            {reading ? (
              <Card>
                <AppText variant="small" muted>{t('workspace.readingNote')}</AppText>
                <AppText variant="heading" testID="reading-season">{t(`report.options.${reading.season}`)}</AppText>
                <Palette colors={Object.values(reading.swatches)} />
                {Object.entries(reading.scores).sort((a, b) => b[1] - a[1]).map(([k, v]) => (
                  <AppText key={k}>{`${t(`report.options.${k}`)} ${Math.round(v * 100)}%`}</AppText>
                ))}
              </Card>
            ) : null}
            {image ? (
              <View>
                <Image source={{ uri: image }} style={styles.image} resizeMode="contain" testID="workspace-image" />
              </View>
            ) : null}
            <Button label={t('workspace.writeReport')} onPress={() => navigation.navigate('ReportEditor', { id })} testID="go-report" />
          </>
        ) : null}
      </ScrollView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  content: { padding: spacing.lg, gap: spacing.md },
  grid: { gap: spacing.sm, flexWrap: 'wrap' },
  swatch: { width: 40, height: 40, borderRadius: radius.md, borderWidth: 2, borderColor: colors.border },
  swatchSelected: { borderColor: colors.text, borderWidth: 3 },
  image: { width: '100%', aspectRatio: 1, borderRadius: radius.md, backgroundColor: colors.surface },
});
