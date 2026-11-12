import React, { useState } from 'react';
import { ActivityIndicator, Image, Linking, Pressable, ScrollView, StyleSheet, View } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { useTranslation } from 'react-i18next';

import { AppText, Card, ErrorBanner, Row, Screen, ScreenHeader } from '../components/ui';
import { useApp } from '../contexts/AppContext';
import type { AppStackParams } from '../navigation/RootNavigator';
import { colors, radius, spacing } from '../theme';
import { errorMessage } from './errorMessage';
import { useLoad } from './useLoad';

type Props = NativeStackScreenProps<AppStackParams, 'Retail'>;

/** Clothing on retailers' sites, matched to the user's results (row 36). */
export function RetailScreen({ navigation }: Props) {
  const { t } = useTranslation();
  const { api, language } = useApp();
  const { data, error, loading } = useLoad(() => api.retail(), [api, language]);
  const [failure, setFailure] = useState<unknown>(null);

  const go = async (id: string) => {
    setFailure(null);
    try {
      const { url } = await api.retailClick(id);
      await Linking.openURL(url);
    } catch (e) {
      setFailure(e);
    }
  };

  return (
    <Screen testID="retail">
      <ScrollView contentContainerStyle={styles.content}>
        <ScreenHeader title={t('retail.title')} onBack={() => navigation.goBack()} />
        <AppText muted>{t('retail.intro')}</AppText>
        {loading && !data ? <ActivityIndicator color={colors.primary} /> : null}
        <ErrorBanner message={error ? errorMessage(error, t) : failure ? errorMessage(failure, t) : null} />
        {data && data.items.length === 0 ? <AppText muted>{t('retail.empty')}</AppText> : null}
        {data?.items.map(item => (
          <Pressable key={item.id} accessibilityRole="link" accessibilityLabel={`${item.title}, ${item.retailer}`}
            onPress={() => go(item.id)} testID={`retail-${item.id}`}>
            <Card>
              <Row style={styles.row}>
                {item.image_url ? <Image source={{ uri: item.image_url }} style={styles.thumb} /> : null}
                <View style={styles.flex}>
                  <AppText variant="heading">{item.title}</AppText>
                  <AppText muted>{item.retailer}{item.price_text ? ` · ${item.price_text}` : ''}</AppText>
                  {item.match ? <AppText variant="small">{t('retail.matched')}</AppText> : null}
                </View>
              </Row>
            </Card>
          </Pressable>
        ))}
      </ScrollView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  content: { padding: spacing.lg, gap: spacing.md },
  row: { gap: spacing.md, alignItems: 'center' },
  thumb: { width: 64, height: 80, borderRadius: radius.md },
});
