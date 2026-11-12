import React, { useEffect, useState } from 'react';
import { ActivityIndicator, Image, Pressable, ScrollView, StyleSheet, View } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { useTranslation } from 'react-i18next';

import { Avatar, AppText, Card, ErrorBanner, Row, Screen, ScreenHeader, SectionTitle, Tag } from '../components/ui';
import { Icon } from '../components/Icon';
import { useApp } from '../contexts/AppContext';
import type { AppStackParams } from '../navigation/RootNavigator';
import { colors, radius, shadows, spacing } from '../theme';
import { errorMessage } from './errorMessage';
import { useLoad } from './useLoad';

/** The consultant's clients (most recent first), each with sessions, photos and colour type. */
export function ClientsScreen({ navigation }: NativeStackScreenProps<AppStackParams, 'Clients'>) {
  const { t } = useTranslation();
  const { api, language } = useApp();
  const list = useLoad(() => api.clients(), [api, language]);
  return (
    <Screen testID="clients">
      <ScrollView contentContainerStyle={styles.content}>
        <ScreenHeader title={t('clients.title')} onBack={() => navigation.goBack()} />
        <AppText muted>{t('clients.intro')}</AppText>
        {list.loading && !list.data ? <ActivityIndicator color={colors.primary} /> : null}
        <ErrorBanner message={list.error ? errorMessage(list.error, t) : null} />
        {list.data && list.data.length === 0 ? <AppText muted>{t('clients.none')}</AppText> : null}
        {list.data?.map(c => (
          <Pressable key={c.id} accessibilityRole="button" testID={`client-${c.id}`}
            onPress={() => navigation.navigate('ClientDetail', { id: c.id, name: c.name })}>
            <Card>
              <Row style={styles.row}>
                <Avatar name={c.name} size={48} />
                <View style={styles.flex}>
                  <AppText variant="heading">{c.name}</AppText>
                  <AppText variant="small" muted>{t('clients.summary', { consultations: c.consultations, photos: c.photos })}</AppText>
                  {c.colour_type ? <Tag label={c.colour_type.title} tone="gold" /> : (
                    <AppText variant="small" muted>{t('clients.noType')}</AppText>
                  )}
                </View>
                <Icon name="arrow-up-right" size={18} color={colors.muted} />
              </Row>
            </Card>
          </Pressable>
        ))}
      </ScrollView>
    </Screen>
  );
}

function ConsultationPhoto({ consultationId, fileId }: { consultationId: string; fileId: string }) {
  const { api } = useApp();
  const [uri, setUri] = useState<string | null>(null);
  useEffect(() => {
    let live = true;
    api.consultationFile(consultationId, fileId).then(u => live && setUri(u)).catch(() => undefined);
    return () => {
      live = false;
    };
  }, [api, consultationId, fileId]);
  return (
    <View style={styles.photo}>
      {uri ? <Image source={{ uri }} style={StyleSheet.absoluteFill} resizeMode="cover" testID={`client-photo-${fileId}`} /> : null}
    </View>
  );
}

/** One client: photos, colour analyses (open to resume or review) and sessions with report status. */
export function ClientDetailScreen({ route, navigation }: NativeStackScreenProps<AppStackParams, 'ClientDetail'>) {
  const { id, name } = route.params;
  const { t } = useTranslation();
  const { api, language } = useApp();
  const detail = useLoad(() => api.clientDetail(id), [api, id, language]);
  const d = detail.data;
  return (
    <Screen testID="client-detail">
      <ScrollView contentContainerStyle={styles.content}>
        <ScreenHeader title={name} onBack={() => navigation.goBack()} />
        {detail.loading && !d ? <ActivityIndicator color={colors.primary} /> : null}
        <ErrorBanner message={detail.error ? errorMessage(detail.error, t) : null} />
        {d ? (
          <>
            <SectionTitle>{t('clients.photos')}</SectionTitle>
            <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.photos}>
              {d.photos.map(p => <ConsultationPhoto key={p.id} consultationId={p.consultation_id} fileId={p.id} />)}
            </ScrollView>

            <SectionTitle>{t('clients.analyses')}</SectionTitle>
            {d.analyses.length === 0 ? <AppText muted>{t('clients.noType')}</AppText> : null}
            {d.analyses.map(a => (
              <Pressable key={a.id} accessibilityRole="button" testID={`analysis-${a.id}`}
                onPress={() => a.file_id && navigation.navigate('DrapingStudio', { id: a.consultation_id, fileId: a.file_id, sessionId: a.id })}>
                <Card>
                  <Row style={styles.row}>
                    <View style={styles.flex}>
                      <AppText variant="heading">{a.colour_type?.title ?? t('clients.inProgress')}</AppText>
                      <AppText variant="small" muted>{a.created_at.slice(0, 10)}</AppText>
                    </View>
                    {a.custom_palette?.length ? (
                      <Row style={styles.mini}>
                        {a.custom_palette.slice(0, 6).map(hex => <View key={hex} style={[styles.dot, { backgroundColor: hex }]} />)}
                      </Row>
                    ) : null}
                  </Row>
                  {a.notes ? <AppText variant="small" muted>{a.notes}</AppText> : null}
                </Card>
              </Pressable>
            ))}

            <SectionTitle>{t('clients.consultations')}</SectionTitle>
            {d.consultations.map(c => (
              <Card key={c.id}>
                <Row style={styles.row}>
                  <View style={styles.flex}>
                    <AppText>{t(`services.${c.kind}`, { defaultValue: c.kind })}</AppText>
                    <AppText variant="small" muted>{`${c.created_at.slice(0, 10)} · ${t(`clients.report.${c.report ?? 'none'}`)}`}</AppText>
                  </View>
                  <Pressable accessibilityRole="button" onPress={() => navigation.navigate('Workspace', { id: c.id })} testID={`client-workspace-${c.id}`}>
                    <AppText style={styles.link}>{t('clients.open')}</AppText>
                  </Pressable>
                </Row>
              </Card>
            ))}
          </>
        ) : null}
      </ScrollView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  content: { padding: spacing.lg, gap: spacing.md },
  flex: { flex: 1, gap: 4 },
  row: { gap: spacing.md, alignItems: 'center' },
  photos: { gap: spacing.sm },
  photo: { width: 96, height: 124, borderRadius: radius.md, overflow: 'hidden', backgroundColor: colors.primarySoft, boxShadow: shadows.soft },
  mini: { gap: 3 },
  dot: { width: 14, height: 14, borderRadius: 7 },
  link: { color: colors.primary, fontWeight: '600' },
});
