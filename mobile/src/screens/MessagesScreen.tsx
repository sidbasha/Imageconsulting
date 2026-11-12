import React, { useCallback, useRef, useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, View } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { useTranslation } from 'react-i18next';

import { ApiError, type SendResult } from '../api/client';
import { AppText, Button, Card, ErrorBanner, Row, Screen, ScreenHeader, TextField } from '../components/ui';
import { useApp } from '../contexts/AppContext';
import type { AppStackParams } from '../navigation/RootNavigator';
import { colors, radius, spacing } from '../theme';
import { errorMessage } from './errorMessage';
import { useLoad } from './useLoad';

/** Conversations with stylists (row 30). */
export function MessagesScreen({ navigation }: NativeStackScreenProps<AppStackParams, 'Messages'>) {
  const { t } = useTranslation();
  const { api } = useApp();
  const { data, error, loading, reload } = useLoad(() => api.threads(), [api]);
  useFocusEffect(useCallback(() => { reload(); }, [reload]));
  return (
    <Screen testID="messages">
      <ScrollView contentContainerStyle={styles.content}>
        <ScreenHeader title={t('messages.title')} onBack={() => navigation.goBack()} />
        {loading && !data ? <ActivityIndicator color={colors.primary} /> : null}
        <ErrorBanner message={error ? errorMessage(error, t) : null} />
        {data && data.length === 0 ? <AppText muted>{t('messages.none')}</AppText> : null}
        {data?.map(th => (
          <Pressable key={th.id} accessibilityRole="button" testID={`thread-${th.id}`}
            onPress={() => navigation.navigate('Thread', { id: th.id, name: th.with.name })}>
            <Card>
              <Row style={styles.row}>
                <AppText variant="heading" style={styles.flex}>{th.with.name}</AppText>
                {th.unread ? <AppText variant="small">{t('messages.unread')}</AppText> : null}
              </Row>
            </Card>
          </Pressable>
        ))}
      </ScrollView>
    </Screen>
  );
}

/** One conversation. Messages with contact details are held back and the sender is told why (rows 31-33). */
export function ThreadScreen({ route, navigation }: NativeStackScreenProps<AppStackParams, 'Thread'>) {
  const { id, name } = route.params;
  const { t } = useTranslation();
  const { api } = useApp();
  const { data, error, loading, reload } = useLoad(() => api.messages(id), [api, id]);
  const [text, setText] = useState('');
  const [warning, setWarning] = useState<SendResult['warning']>(null);
  const [failure, setFailure] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const scroll = useRef<React.ComponentRef<typeof ScrollView>>(null);

  const send = async () => {
    if (!text.trim()) {
      return;
    }
    setBusy(true);
    setFailure(null);
    try {
      const result = await api.sendMessage(id, text.trim());
      setWarning(result.warning);
      setText('');
      await reload();
      scroll.current?.scrollToEnd();
    } catch (e) {
      setFailure(e);
    } finally {
      setBusy(false);
    }
  };
  const suspended = failure instanceof ApiError && ['messaging_suspended', 'messaging_banned'].includes(failure.code);

  return (
    <Screen testID="thread">
      <ScrollView ref={scroll} contentContainerStyle={styles.content}>
        <ScreenHeader title={name} onBack={() => navigation.goBack()} />
        <AppText variant="small" muted>
          {t('messages.policy')}
        </AppText>
        {loading && !data ? <ActivityIndicator color={colors.primary} /> : null}
        <ErrorBanner message={error ? errorMessage(error, t) : null} />
        {data?.map(m => (
          <Row key={m.id} style={m.mine ? styles.mineRow : undefined}>
            <View style={[styles.bubble, m.mine ? styles.mine : styles.theirs, m.status === 'not_delivered' && styles.held]} testID={`message-${m.id}`}>
              <AppText>{m.body}</AppText>
              {m.status === 'not_delivered' ? <AppText variant="small" style={styles.heldText}>{t('messages.notDelivered')}</AppText> : null}
            </View>
          </Row>
        ))}
        {warning ? (
          <Card style={styles.warning}>
            <AppText testID="message-warning">{t(`messages.warning.${warning.code}`)}</AppText>
            {warning.consequence && warning.consequence !== 'none' ? (
              <AppText variant="small">{t(`messages.consequence.${warning.consequence}`)}</AppText>
            ) : null}
          </Card>
        ) : null}
        <ErrorBanner message={failure ? errorMessage(failure, t) : null} />
        {!suspended ? (
          <>
            <TextField label={t('messages.write')} value={text} onChangeText={setText} multiline testID="message-input" />
            <Button label={t('messages.send')} onPress={send} loading={busy} testID="send-message" />
          </>
        ) : null}
      </ScrollView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  content: { padding: spacing.lg, gap: spacing.md },
  row: { gap: spacing.sm, alignItems: 'center' },
  mineRow: { justifyContent: 'flex-end' },
  bubble: { maxWidth: '80%', padding: spacing.md, borderRadius: radius.md },
  mine: { backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.primary },
  theirs: { backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border },
  held: { borderColor: colors.danger, borderStyle: 'dashed' },
  heldText: { color: colors.danger },
  warning: { borderColor: colors.danger },
});
