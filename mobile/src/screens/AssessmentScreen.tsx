import React, { useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { useTranslation } from 'react-i18next';

import type { AnalysisKind, AssessmentResult, Questionnaire } from '../api/client';
import { AppText, Bullets, Button, Card, ErrorBanner, Palette, Row, Screen, ScreenHeader } from '../components/ui';
import { useApp } from '../contexts/AppContext';
import type { AppStackParams } from '../navigation/RootNavigator';
import { colors, gradients, radius, shadows, spacing } from '../theme';
import { errorMessage } from './errorMessage';
import { useLoad } from './useLoad';

type Props = NativeStackScreenProps<AppStackParams, 'Assessment'>;

// Questionnaires that also have an automated photo analysis (rows 7-9).
const PHOTO_ANALYSIS: Record<string, AnalysisKind> = { face_shape: 'face_shape', body_shape: 'body_shape', seasonal_color: 'seasonal_color' };

/**
 * One screen for every questionnaire: shows the latest result if there is
 * one, otherwise (or on "Retake") walks through the questions one at a time.
 */
export function AssessmentScreen({ route, navigation }: Props) {
  const { key } = route.params;
  const { t } = useTranslation();
  const { api, language, features } = useApp();
  const photoKind = PHOTO_ANALYSIS[key];
  const canUsePhoto = !!photoKind && (features ?? []).includes('phase1.photo_assessment');
  const { data, setData, error, loading, reload } = useLoad(
    async () => {
      const [questionnaire, result] = await Promise.all([api.questionnaire(key), api.latestResult(key)]);
      return { questionnaire, result };
    },
    [api, key, language],
  );
  const [retaking, setRetaking] = useState(false);

  return (
    <Screen testID="assessment">
      <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
        <ScreenHeader title={data?.questionnaire.title ?? ''} onBack={() => navigation.goBack()} />
        {loading && !data ? <ActivityIndicator color={colors.primary} accessibilityLabel={t('common.loading')} /> : null}
        {error ? (
          <View style={styles.gap}>
            <ErrorBanner message={errorMessage(error, t)} />
            <Button label={t('common.retry')} onPress={reload} testID="retry" />
          </View>
        ) : null}
        {canUsePhoto && data ? (
          <Card>
            <AppText>{t('assessment.photoOption')}</AppText>
            <Button kind="link" label={t('assessment.usePhoto')} testID="use-photo"
              onPress={() => navigation.navigate('PhotoAnalysis', { kind: photoKind })} />
          </Card>
        ) : null}
        {data && data.result && !retaking ? (
          <ResultView result={data.result} onRetake={() => setRetaking(true)} />
        ) : null}
        {data && (!data.result || retaking) ? (
          <Runner
            // Restart from the first question if the language (and so the text) changes mid-way.
            key={language}
            questionnaire={data.questionnaire}
            submit={answers => api.submitAnswers(key, answers)}
            onDone={result => {
              setData({ questionnaire: data.questionnaire, result });
              setRetaking(false);
            }}
          />
        ) : null}
      </ScrollView>
    </Screen>
  );
}

type RunnerProps = {
  questionnaire: Questionnaire;
  submit: (answers: Record<string, string>) => Promise<AssessmentResult>;
  onDone: (result: AssessmentResult) => void;
};

function Runner({ questionnaire, submit, onDone }: RunnerProps) {
  const { t } = useTranslation();
  const [started, setStarted] = useState(false);
  const [index, setIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<unknown>(null);

  if (!started) {
    return (
      <View style={styles.gap}>
        <AppText muted>{questionnaire.intro}</AppText>
        <Button label={t('assessment.start')} onPress={() => setStarted(true)} testID="start" />
      </View>
    );
  }

  const total = questionnaire.questions.length;
  const question = questionnaire.questions[index];
  const chosen = answers[question.key];
  const last = index === total - 1;

  const next = async () => {
    if (!last) {
      setIndex(index + 1);
      return;
    }
    setBusy(true);
    setFailure(null);
    try {
      onDone(await submit(answers));
    } catch (e) {
      setFailure(e);
      setBusy(false);
    }
  };

  return (
    <View style={styles.gap}>
      <AppText variant="small" muted testID="progress">
        {t('assessment.progress', { current: index + 1, total })}
      </AppText>
      <View style={styles.track}>
        <View style={[styles.fill, { width: `${((index + 1) / total) * 100}%`, backgroundImage: gradients.primary }]} />
      </View>
      <AppText variant="heading" accessibilityRole="header">
        {question.prompt}
      </AppText>
      <View style={styles.gap} accessibilityRole="radiogroup">
        {question.options.map(option => {
          const selected = option.key === chosen;
          return (
            <Pressable
              key={option.key}
              accessibilityRole="radio"
              accessibilityState={{ selected }}
              accessibilityLabel={option.label}
              testID={`option-${option.key}`}
              onPress={() => setAnswers({ ...answers, [question.key]: option.key })}
              style={({ pressed }) => [styles.option, { boxShadow: shadows.soft }, selected && styles.optionSelected,
                pressed && styles.optionPressed]}>
              <Row style={styles.optionRow}>
                <AppText style={[styles.flexText, selected ? styles.optionLabelSelected : undefined]}>{option.label}</AppText>
                <View style={[styles.radio, selected && { backgroundImage: gradients.primary, borderColor: colors.primary }]}>
                  {selected ? <Text style={styles.check}>✓</Text> : null}
                </View>
              </Row>
            </Pressable>
          );
        })}
      </View>
      <ErrorBanner message={failure ? errorMessage(failure, t) : null} />
      {/* "Next" appears once the question is answered, so an incomplete set can never be sent. */}
      {chosen ? (
        <Button label={t(last ? 'assessment.finish' : 'assessment.next')} onPress={next} loading={busy} testID="next" />
      ) : null}
      {index > 0 ? (
        <Button kind="link" label={t('assessment.previous')} onPress={() => setIndex(index - 1)} testID="previous" />
      ) : null}
    </View>
  );
}

function ResultView({ result, onRetake }: { result: AssessmentResult; onRetake: () => void }) {
  const { t } = useTranslation();
  const profile = result.profile;
  return (
    <View style={styles.gap} testID="result">
      {profile ? (
        <Card>
          <AppText variant="title" testID="result-title">
            {profile.title}
          </AppText>
          <AppText>{profile.summary}</AppText>
          <AppText variant="small" muted>
            {t('assessment.selfAssessed')}
          </AppText>
        </Card>
      ) : (
        <Card>
          <AppText>{t('assessment.saved')}</AppText>
        </Card>
      )}

      {profile?.palette ? (
        <Card>
          <AppText variant="heading">{t('assessment.palette')}</AppText>
          <Palette colors={profile.palette} />
        </Card>
      ) : null}

      {profile
        ? Object.entries(profile.advice).map(([category, items]) => (
            <Card key={category}>
              <AppText variant="heading">{t(`assessment.advice.${category}`)}</AppText>
              <Bullets items={items} />
            </Card>
          ))
        : null}

      <Card>
        <AppText variant="heading">{t('assessment.yourAnswers')}</AppText>
        {result.answers.map(item => (
          <View key={item.question}>
            <AppText variant="small" muted>
              {item.question}
            </AppText>
            <AppText>{item.answer}</AppText>
          </View>
        ))}
      </Card>

      <Row>
        <Button kind="link" label={t('assessment.retake')} onPress={onRetake} testID="retake" />
      </Row>
    </View>
  );
}

const styles = StyleSheet.create({
  content: { padding: spacing.lg, gap: spacing.lg },
  gap: { gap: spacing.md },
  option: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.md,
    padding: spacing.md,
    minHeight: 52,
    justifyContent: 'center',
  },
  optionSelected: { borderColor: colors.primary, borderWidth: 1.5, backgroundColor: colors.primarySoft },
  optionLabelSelected: { fontWeight: '600', color: colors.primaryDeep },
  optionPressed: { transform: [{ scale: 0.985 }] },
  optionRow: { gap: spacing.md, alignItems: 'center' },
  flexText: { flex: 1 },
  radio: { width: 26, height: 26, borderRadius: 13, borderWidth: 1.5, borderColor: colors.border, alignItems: 'center', justifyContent: 'center' },
  check: { color: colors.onPrimary, fontSize: 14, fontWeight: '700' },
  track: { height: 6, borderRadius: 3, backgroundColor: colors.primarySoft, overflow: 'hidden' },
  fill: { height: 6, borderRadius: 3 },
});
