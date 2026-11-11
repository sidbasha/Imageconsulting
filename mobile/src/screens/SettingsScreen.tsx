import React, { useState } from 'react';
import { ScrollView, StyleSheet, View } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { useTranslation } from 'react-i18next';

import { AppText, Button, LanguageSwitch, Row, Screen } from '../components/ui';
import { useApp } from '../contexts/AppContext';
import type { AppStackParams } from '../navigation/RootNavigator';
import { colors, radius, spacing } from '../theme';

export function SettingsScreen({ navigation }: NativeStackScreenProps<AppStackParams, 'Settings'>) {
  const { t } = useTranslation();
  const { user, signOut, rtl } = useApp();
  const [busy, setBusy] = useState(false);

  return (
    <Screen testID="settings">
      <ScrollView contentContainerStyle={styles.content}>
        <Row style={styles.top}>
          <Button kind="link" label={`${rtl ? '›' : '‹'} ${t('common.back')}`} onPress={() => navigation.goBack()} testID="back" />
        </Row>
        <AppText variant="title" accessibilityRole="header">
          {t('settings.title')}
        </AppText>

        <View style={styles.card}>
          <AppText variant="small" muted>
            {t('settings.account')}
          </AppText>
          <AppText variant="heading">{user?.full_name}</AppText>
          <AppText muted>{user?.email}</AppText>
        </View>

        <View style={styles.card}>
          <AppText variant="small" muted>
            {t('language.label')}
          </AppText>
          <LanguageSwitch />
        </View>

        <Button
          label={t('auth.signOut')}
          loading={busy}
          testID="sign-out"
          onPress={async () => {
            setBusy(true);
            await signOut();
          }}
        />
      </ScrollView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  content: { padding: spacing.lg, gap: spacing.lg },
  top: { justifyContent: 'flex-start' },
  card: {
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.border,
    padding: spacing.md,
    gap: spacing.sm,
  },
});
