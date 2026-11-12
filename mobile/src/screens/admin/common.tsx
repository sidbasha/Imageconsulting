import React, { useState } from 'react';
import { ActivityIndicator, RefreshControl, ScrollView, StyleSheet } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { useTranslation } from 'react-i18next';

import { AppText, ErrorBanner, Screen, ScreenHeader } from '../../components/ui';
import { colors, spacing } from '../../theme';
import { errorMessage } from '../errorMessage';

/** Staff areas (Feature List rows 53-60) and the permission each needs. */
export const ADMIN_SECTIONS = [
  { key: 'approvals', permission: 'users.review', icon: 'id-card', screen: 'AdminApprovals', count: '/admin/eligibility', count2: '/admin/identity/pending' },
  { key: 'stylists', permission: 'stylists.review', icon: 'badge', screen: 'AdminStylists', count: '/admin/stylists?status_filter=submitted' },
  { key: 'orders', permission: 'orders.manage', icon: 'receipt', screen: 'AdminOrders', count: '/admin/orders?status_filter=refund_due' },
  { key: 'moderation', permission: 'moderation.manage', icon: 'flag', screen: 'AdminModeration', count: '/admin/moderation/violations' },
  { key: 'catalogue', permission: 'content.manage', icon: 'package', screen: 'AdminCatalogue' },
  { key: 'tryOn', permission: 'content.manage', icon: 'images', screen: 'AdminTryOn' },
  { key: 'retail', permission: 'content.manage', icon: 'link', screen: 'AdminRetail' },
  { key: 'plans', permission: 'pricing.manage', icon: 'crown', screen: 'AdminPlans' },
  { key: 'promotions', permission: 'promotions.manage', icon: 'megaphone', screen: 'AdminPromotions', count: '/admin/promotions/campaigns?status_filter=pending_review' },
  { key: 'rewards', permission: 'rewards.manage', icon: 'gem', screen: 'AdminRewards' },
  { key: 'settings', permission: 'settings.manage', icon: 'sliders', screen: 'AdminSettings' },
] as const;

export const isStaff = (permissions: string[] | undefined) =>
  ADMIN_SECTIONS.some(s => (permissions ?? []).includes(s.permission));

/** Page frame for an admin screen: header, pull to refresh, errors. */
export function AdminPage({ title, intro, loading, error, onRefresh, children, testID }: {
  title: string; intro?: string; loading?: boolean; error?: unknown; onRefresh?: () => void; children: React.ReactNode; testID?: string;
}) {
  const { t } = useTranslation();
  const navigation = useNavigation();
  return (
    <Screen testID={testID}>
      <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled"
        refreshControl={onRefresh ? <RefreshControl refreshing={false} onRefresh={onRefresh} tintColor={colors.primary} /> : undefined}>
        <ScreenHeader title={title} onBack={() => navigation.goBack()} />
        {intro ? <AppText muted>{intro}</AppText> : null}
        <ErrorBanner message={error ? errorMessage(error, t) : null} />
        {loading ? <ActivityIndicator color={colors.primary} /> : null}
        {children}
      </ScrollView>
    </Screen>
  );
}

/** Runs one action at a time, remembering which is busy and the last failure. */
export function useAction() {
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [done, setDone] = useState<string | null>(null);
  const run = async (key: string, action: () => Promise<unknown>, message?: string) => {
    setBusy(key);
    setError(null);
    setDone(null);
    try {
      await action();
      if (message) {
        setDone(message);
      }
      return true;
    } catch (e) {
      setError(e);
      return false;
    } finally {
      setBusy(null);
    }
  };
  return { busy, error, done, run };
}

export const day = (iso: string | null | undefined) => (iso ? iso.slice(0, 16).replace('T', ' ') : '');

const styles = StyleSheet.create({ content: { padding: spacing.lg, gap: spacing.md, paddingBottom: 130 } });
