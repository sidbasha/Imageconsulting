import React from 'react';
import { ActivityIndicator, ScrollView, StyleSheet, View } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { useTranslation } from 'react-i18next';

import { AppText, Bullets, Button, Card, ErrorBanner, Palette, Screen, ScreenHeader } from '../components/ui';
import { useApp } from '../contexts/AppContext';
import type { AppStackParams } from '../navigation/RootNavigator';
import { colors, spacing } from '../theme';
import { errorMessage } from './errorMessage';
import { useLoad } from './useLoad';

type Props = NativeStackScreenProps<AppStackParams, 'Recommendations'>;

export function RecommendationsScreen({ route, navigation }: Props) {
  const { category } = route.params;
  const { t } = useTranslation();
  const { api, language } = useApp();
  const { data, error, loading, reload } = useLoad(() => api.recommendations(category), [api, category, language]);

  // Coming back from an assessment taken via the prompt below: show the new advice.
  const first = React.useRef(true);
  useFocusEffect(
    React.useCallback(() => {
      if (first.current) {
        first.current = false;
        return;
      }
      reload();
    }, [reload]),
  );

  const missing = data?.missing ?? [];

  return (
    <Screen testID="recommendations">
      <ScrollView contentContainerStyle={styles.content}>
        <ScreenHeader title={t(`recommendations.title.${category}`)} onBack={() => navigation.goBack()} />
        {loading && !data ? <ActivityIndicator color={colors.primary} accessibilityLabel={t('common.loading')} /> : null}
        {error ? (
          <View style={styles.gap}>
            <ErrorBanner message={errorMessage(error, t)} />
            <Button label={t('common.retry')} onPress={reload} testID="retry" />
          </View>
        ) : null}

        {data && data.sections.length === 0 ? <AppText muted>{t('recommendations.empty')}</AppText> : null}

        {data?.sections.map(section => (
          <Card key={section.source}>
            <AppText variant="small" muted>
              {t('recommendations.basedOn', { source: section.source_title, result: section.result })}
            </AppText>
            {section.palette ? <Palette colors={section.palette} /> : null}
            <Bullets items={section.items} />
          </Card>
        ))}

        {missing.length ? (
          <View style={styles.gap}>
            <AppText variant="heading">{t('recommendations.missing')}</AppText>
            {missing.map(item => (
              <Button
                key={item.key}
                label={item.title}
                testID={`take-${item.key}`}
                onPress={() => navigation.navigate('Assessment', { key: item.key })}
              />
            ))}
          </View>
        ) : null}
      </ScrollView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  content: { padding: spacing.lg, gap: spacing.lg },
  gap: { gap: spacing.md },
});
