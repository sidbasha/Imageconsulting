import React, { useEffect, useState } from 'react';
import { ActivityIndicator, Image, ScrollView, StyleSheet, View } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { useTranslation } from 'react-i18next';

import type { ReportSection, ReportTemplate, TemplateSection } from '../api/client';
import { AppText, Button, Card, Chips, ErrorBanner, Palette, Screen, ScreenHeader, TextField } from '../components/ui';
import { useApp } from '../contexts/AppContext';
import type { AppStackParams } from '../navigation/RootNavigator';
import { colors, radius, spacing } from '../theme';
import { errorMessage } from './errorMessage';
import { useLoad } from './useLoad';

type Props = NativeStackScreenProps<AppStackParams, 'ReportEditor'>;
const HEX = /^#[0-9a-fA-F]{6}$/;

function asValues(sections: ReportSection[]): Record<string, string> {
  const out: Record<string, string> = {};
  for (const s of sections) {
    out[s.key] = Array.isArray(s.value) ? s.value.join(s.type === 'palette' ? ', ' : '\n') : typeof s.value === 'object' ? s.value.key : String(s.value);
  }
  return out;
}

/**
 * The stylist writes the standard expert report (rows 24, 25) for one
 * consultation. Fields come from the report template the admin manages (56):
 * choices as chips, text as paragraphs, lists one item per line, palettes as
 * colour codes. The customer sees nothing until it is delivered.
 */
export function ReportEditorScreen({ route, navigation }: Props) {
  const { id } = route.params;
  const { t } = useTranslation();
  const { api, language } = useApp();
  const loaded = useLoad(async () => {
    const [template, consultation] = await Promise.all([api.reportTemplate(id), api.consultation(id)]);
    return { template, consultation };
  }, [api, id, language]);
  const [values, setValues] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState<string | null>(null);
  const [failure, setFailure] = useState<unknown>(null);
  const [saved, setSaved] = useState<string | null>(null);

  // Finished guided draping analyses for this client can fill the report's colour fields.
  const drapings = useLoad(
    () => api.drapingSessions(id).then(list => list.filter(d => d.status === 'complete')).catch(() => []),
    [api, id, language],
  );

  useEffect(() => {
    const report = loaded.data?.consultation.report;
    if (report) {
      setValues(asValues(report.sections));
    }
  }, [loaded.data]);

  const fillFromDraping = async (sessionId: string) => {
    setBusy(`fill-${sessionId}`);
    setFailure(null);
    try {
      const report = await api.reportFromDraping(id, sessionId);
      setValues(old => ({ ...old, ...asValues(report.sections) }));
      setSaved('filled');
    } catch (e) {
      setFailure(e);
    } finally {
      setBusy(null);
    }
  };

  const content = (template: ReportTemplate) => {
    const out: Record<string, unknown> = {};
    for (const s of template.sections) {
      const raw = (values[s.key] ?? '').trim();
      if (!raw) {
        continue;
      }
      out[s.key] = s.type === 'list' ? raw.split('\n').map(x => x.trim()).filter(Boolean)
        : s.type === 'palette' ? raw.split(/[\s,]+/).filter(Boolean) : raw;
    }
    return out;
  };

  const save = async (deliver: boolean) => {
    if (!loaded.data) {
      return;
    }
    setBusy(deliver ? 'deliver' : 'save');
    setFailure(null);
    setSaved(null);
    try {
      await api.saveReport(id, content(loaded.data.template));
      if (deliver) {
        await api.deliverReport(id);
      }
      setSaved(deliver ? 'delivered' : 'saved');
    } catch (e) {
      setFailure(e);
    } finally {
      setBusy(null);
    }
  };

  const data = loaded.data;
  const delivered = data?.consultation.report?.status === 'delivered' || saved === 'delivered';
  return (
    <Screen testID="report-editor">
      <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
        <ScreenHeader title={data?.template.title ?? ''} onBack={() => navigation.goBack()} />
        {loaded.loading && !data ? <ActivityIndicator color={colors.primary} /> : null}
        <ErrorBanner message={loaded.error ? errorMessage(loaded.error, t) : failure ? errorMessage(failure, t) : null} />
        {data ? (
          <>
            {Object.keys(data.consultation.intake).length ? (
              <Card>
                <AppText variant="heading">{t('report.aboutClient')}</AppText>
                {Object.entries(data.consultation.intake).map(([k, v]) => (
                  <AppText key={k}>{`${t(`consultation.intake.${k}`, { defaultValue: k })}: ${v}`}</AppText>
                ))}
              </Card>
            ) : null}
            {data.consultation.files.length ? (
              <Card>
                <AppText variant="heading">{t('consultation.photos')}</AppText>
                {data.consultation.files.map(f => (
                  <FileReview key={f.id} consultationId={id} file={f} withVerdict={data.consultation.kind === 'makeup_audit'} />
                ))}
              </Card>
            ) : null}
            {delivered ? <AppText testID="report-delivered">{t('report.delivered')}</AppText> : null}
            {!delivered && data.template.sections.some(s => s.key === 'colour_type') && (drapings.data ?? []).length ? (
              <Card style={styles.fill}>
                <AppText variant="heading">{t('report.fromDraping')}</AppText>
                <AppText variant="small" muted>{t('report.fromDrapingNote')}</AppText>
                {(drapings.data ?? []).map(d => (
                  <Button key={d.id} kind="soft" testID={`fill-${d.id}`} loading={busy === `fill-${d.id}`}
                    label={`${d.result?.colour_type.title ?? ''} · ${d.created_at.slice(0, 10)}`} onPress={() => fillFromDraping(d.id)} />
                ))}
                {saved === 'filled' ? <AppText variant="small" testID="report-filled">{t('report.filled')}</AppText> : null}
              </Card>
            ) : null}
            {data.template.sections.map(s => (
              <Field key={s.key} section={s} value={values[s.key] ?? ''} disabled={delivered}
                onChange={v => setValues(old => ({ ...old, [s.key]: v }))} />
            ))}
            {saved === 'saved' ? <AppText testID="report-saved">{t('report.saved')}</AppText> : null}
            {!delivered ? (
              <>
                <Button kind="link" label={t('report.saveDraft')} onPress={() => save(false)} loading={busy === 'save'} testID="save-report" />
                <Button label={t('report.deliver')} onPress={() => save(true)} loading={busy === 'deliver'} testID="deliver-report" />
              </>
            ) : null}
          </>
        ) : null}
      </ScrollView>
    </Screen>
  );
}

function Field({ section, value, onChange, disabled }: { section: TemplateSection; value: string; onChange: (v: string) => void; disabled: boolean }) {
  const { t } = useTranslation();
  const label = `${section.title}${section.required ? ' *' : ''}`;
  if (section.type === 'decision' || section.type === 'choice') {
    return (
      <Chips label={label} value={value || null} onChange={v => !disabled && onChange(v)} testID={`field-${section.key}`} scroll={section.options.length > 5}
        options={section.options.map(o => ({ value: o, label: t(`report.options.${o}`, { defaultValue: o }) }))} />
    );
  }
  const palette = section.type === 'palette' ? value.split(/[\s,]+/).filter(c => HEX.test(c)) : [];
  return (
    <View>
      <TextField label={label} value={value} onChangeText={onChange} editable={!disabled} multiline={section.type !== 'palette'}
        hint={section.type === 'list' ? t('report.onePerLine') : section.type === 'palette' ? t('report.paletteHint') : undefined}
        autoCapitalize={section.type === 'palette' ? 'none' : 'sentences'} testID={`field-${section.key}`} />
      {palette.length ? <Palette colors={palette} /> : null}
    </View>
  );
}

function FileReview({ consultationId, file, withVerdict }: {
  consultationId: string; file: { id: string; purpose: string; caption: string | null; verdict: { verdict: string } | null }; withVerdict: boolean;
}) {
  const { t } = useTranslation();
  const { api } = useApp();
  const [uri, setUri] = useState<string | null>(null);
  const [verdict, setVerdict] = useState<string | null>(file.verdict?.verdict ?? null);
  useEffect(() => {
    let live = true;
    api.consultationFile(consultationId, file.id).then(u => live && setUri(u)).catch(() => undefined);
    return () => {
      live = false;
    };
  }, [api, consultationId, file.id]);
  return (
    <View style={styles.file}>
      {uri ? <Image source={{ uri }} style={styles.photo} resizeMode="cover" /> : null}
      <AppText variant="small">{`${t(`consultation.purpose.${file.purpose}`)}${file.caption ? `: ${file.caption}` : ''}`}</AppText>
      {withVerdict && file.purpose === 'product' ? (
        <Chips value={verdict} testID={`verdict-${file.id}`}
          onChange={async v => { setVerdict(v); await api.setVerdict(consultationId, file.id, v).catch(() => setVerdict(null)); }}
          options={['suits', 'adjust', 'avoid'].map(v => ({ value: v, label: t(`consultation.verdict.${v}`) }))} />
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  fill: { gap: spacing.sm, borderColor: colors.gold, borderWidth: 1 },
  content: { padding: spacing.lg, gap: spacing.md },
  file: { gap: spacing.xs },
  photo: { width: '100%', aspectRatio: 1, borderRadius: radius.md },
});
