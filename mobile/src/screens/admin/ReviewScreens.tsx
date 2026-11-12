/** Staff review queues: approvals (rows 1, 2, 53), stylists (15-17, 54), orders (41, 48), moderation (31-33, 45, 58). */
import React, { useState } from 'react';
import { Alert, Image, StyleSheet, View } from 'react-native';
import { useTranslation } from 'react-i18next';

import { AppText, Button, Card, Chips, ErrorBanner, Rating, Row, SectionTitle, Tag, TextField, money } from '../../components/ui';
import { useApp } from '../../contexts/AppContext';
import { radius, spacing } from '../../theme';
import { errorMessage } from '../errorMessage';
import { useLoad } from '../useLoad';
import { AdminPage, day, useAction } from './common';

// ---------------------------------------------------------------- approvals

export function AdminApprovalsScreen() {
  const { t } = useTranslation();
  const { api } = useApp();
  const [status, setStatus] = useState<string | null>('pending_review');
  const queue = useLoad(() => api.call<any[]>('GET', `/admin/eligibility?status_filter=${status}`), [api, status]);
  const docs = useLoad(() => api.call<any[]>('GET', '/admin/identity/pending'), [api]);
  const action = useAction();
  const decide = (id: string, approve: boolean) =>
    action.run(id, async () => {
      await api.call('POST', `/admin/eligibility/${id}`, { approve });
      await queue.reload();
    });
  return (
    <AdminPage title={t('admin.sections.approvals')} loading={queue.loading && !queue.data} error={queue.error ?? docs.error ?? action.error}
      onRefresh={() => { queue.reload(); docs.reload(); }} testID="admin-approvals">
      <SectionTitle>{t('admin.approvals.identity')}</SectionTitle>
      {docs.data?.length === 0 ? <AppText muted>{t('admin.none')}</AppText> : null}
      {docs.data?.map(d => <DocumentReview key={d.id} item={d} onDone={docs.reload} />)}
      <SectionTitle>{t('admin.approvals.eligibility')}</SectionTitle>
      <Chips scroll value={status} onChange={setStatus} testID="eligibility-status"
        options={['pending_review', 'ineligible', 'incomplete', 'eligible'].map(s => ({ value: s, label: t(`profile.status.${s}`) }))} />
      {queue.data?.length === 0 ? <AppText muted>{t('admin.none')}</AppText> : null}
      {queue.data?.map(q => (
        <Card key={q.user_id}>
          <AppText variant="heading">{q.full_name}</AppText>
          <AppText variant="small" muted>{q.email}</AppText>
          <Row style={styles.tags}>
            {q.reasons.map((r: string) => <Tag key={r} label={t(`profile.reasons.${r}`, { defaultValue: r })} tone="gold" />)}
            <Tag label={t(`identity.status.${q.identity_status}`)} tone="lilac" />
          </Row>
          <Row style={styles.actions}>
            <View style={styles.flex}><Button kind="soft" label={t('admin.reject')} onPress={() => decide(q.user_id, false)} loading={action.busy === q.user_id} /></View>
            <View style={styles.flex}><Button label={t('admin.approve')} onPress={() => decide(q.user_id, true)} testID={`approve-${q.email}`} /></View>
          </Row>
        </Card>
      ))}
    </AdminPage>
  );
}

function DocumentReview({ item, onDone }: { item: any; onDone: () => void }) {
  const { t } = useTranslation();
  const { api } = useApp();
  const [images, setImages] = useState<string[]>([]);
  const [dob, setDob] = useState('');
  const [gender, setGender] = useState<string | null>('female');
  const [reason, setReason] = useState('');
  const action = useAction();
  const show = () =>
    action.run('show', async () => {
      const urls: string[] = [];
      for (let i = 0; i < item.documents; i++) {
        urls.push(await api.image(`/admin/identity/${item.id}/documents/${i}`));
      }
      setImages(urls);
    });
  const review = (approve: boolean) =>
    action.run('review', async () => {
      await api.call('POST', `/admin/identity/${item.id}/review`, approve ? { approve, date_of_birth: dob, gender } : { approve, reason: reason || null });
      onDone();
    });
  return (
    <Card>
      <AppText variant="heading">{item.full_name}</AppText>
      <AppText variant="small" muted>{`${item.email} · ${day(item.created_at)}`}</AppText>
      {images.length ? images.map(u => <Image key={u} source={{ uri: u }} style={styles.doc} resizeMode="contain" />)
        : <Button kind="soft" label={t('admin.approvals.showDocument', { count: item.documents })} onPress={show} loading={action.busy === 'show'} />}
      <AppText variant="small" muted>{t('admin.approvals.readOff')}</AppText>
      <TextField label={t('profile.dob')} hint="1990-05-01" value={dob} onChangeText={setDob} />
      <Chips value={gender} onChange={setGender} options={[{ value: 'female', label: t('profile.female') }, { value: 'male', label: t('profile.male') }]} />
      <TextField label={t('admin.approvals.reason')} value={reason} onChangeText={setReason} />
      <ErrorBanner message={action.error ? errorMessage(action.error, t) : null} />
      <Row style={styles.actions}>
        <View style={styles.flex}><Button kind="soft" label={t('admin.reject')} onPress={() => review(false)} /></View>
        <View style={styles.flex}><Button label={t('admin.verify')} onPress={() => review(true)} loading={action.busy === 'review'} /></View>
      </Row>
    </Card>
  );
}

// ---------------------------------------------------------------- stylists

export function AdminStylistsScreen() {
  const { t } = useTranslation();
  const { api } = useApp();
  const [status, setStatus] = useState<string | null>('submitted');
  const list = useLoad(() => api.call<any[]>('GET', `/admin/stylists?status_filter=${status}`), [api, status]);
  return (
    <AdminPage title={t('admin.sections.stylists')} intro={t('admin.stylists.intro')} loading={list.loading && !list.data} error={list.error}
      onRefresh={list.reload} testID="admin-stylists">
      <Chips scroll value={status} onChange={setStatus} options={['submitted', 'approved', 'rejected', 'suspended'].map(s => ({ value: s, label: t(`application.status.${s}`) }))} />
      {list.data?.length === 0 ? <AppText muted>{t('admin.none')}</AppText> : null}
      {list.data?.map(a => <ApplicationCard key={a.id} application={a} onChange={list.reload} />)}
    </AdminPage>
  );
}

function ApplicationCard({ application: a, onChange }: { application: any; onChange: () => void }) {
  const { t } = useTranslation();
  const { api } = useApp();
  const [note, setNote] = useState('');
  const [preview, setPreview] = useState<string | null>(null);
  const action = useAction();
  const review = (id: string, approve: boolean) =>
    action.run(id, async () => {
      await api.call('POST', `/admin/stylists/credentials/${id}/review`, { approve });
      onChange();
    });
  const open = (c: any) =>
    action.run(c.id, async () => {
      if (c.title.toLowerCase().endsWith('.pdf')) {
        return;
      }
      setPreview(await api.image(`/admin/stylists/credentials/${c.id}/file`));
    });
  const decide = (approve: boolean) =>
    action.run('decide', async () => {
      await api.call('POST', `/admin/stylists/${a.id}/decision`, { approve, note: note || null });
      onChange();
    });
  return (
    <Card>
      <AppText variant="heading">{a.display_name}</AppText>
      <AppText variant="small" muted>{[a.city, a.years_experience !== null ? t('admin.stylists.years', { count: a.years_experience }) : null].filter(Boolean).join(' · ')}</AppText>
      {a.bio ? <AppText>{a.bio}</AppText> : null}
      {a.credentials.map((c: any) => (
        <View key={c.id} style={styles.line}>
          <Row style={styles.lineRow}>
            <View style={styles.flex}>
              <AppText style={styles.bold}>{c.title}</AppText>
              <AppText variant="small" muted>{t(`application.kinds.${c.kind}`, { defaultValue: c.kind })}</AppText>
            </View>
            <Tag label={t(`application.credentialStatus.${c.status}`)} tone={c.status === 'accepted' ? 'sage' : c.status === 'rejected' ? 'rose' : 'gold'} />
          </Row>
          <Row style={styles.actions}>
            <Button kind="link" label={t('admin.view')} onPress={() => open(c)} />
            <Button kind="link" label={t('admin.accept')} onPress={() => review(c.id, true)} testID={`accept-${c.id}`} />
            <Button kind="link" label={t('admin.reject')} onPress={() => review(c.id, false)} />
          </Row>
        </View>
      ))}
      {preview ? <Image source={{ uri: preview }} style={styles.doc} resizeMode="contain" /> : null}
      <TextField label={t('admin.stylists.note')} value={note} onChangeText={setNote} />
      <ErrorBanner message={action.error ? errorMessage(action.error, t) : null} />
      <Row style={styles.actions}>
        <View style={styles.flex}><Button kind="soft" label={a.status === 'approved' ? t('admin.suspend') : t('admin.reject')} onPress={() => decide(false)} /></View>
        {a.status !== 'approved' ? <View style={styles.flex}><Button label={t('admin.approve')} onPress={() => decide(true)} loading={action.busy === 'decide'} testID={`approve-${a.id}`} /></View> : null}
      </Row>
    </Card>
  );
}

// ---------------------------------------------------------------- orders

export function AdminOrdersScreen() {
  const { t } = useTranslation();
  const { api } = useApp();
  const [status, setStatus] = useState<string | null>('');
  const list = useLoad(() => api.call<any[]>('GET', `/admin/orders${status ? `?status_filter=${status}` : ''}`), [api, status]);
  const action = useAction();
  const refund = (o: any) =>
    Alert.alert(t('admin.orders.refundTitle'), t('admin.orders.refundBody', { amount: money(o.amount_minor, o.currency) }), [
      { text: t('admin.cancel'), style: 'cancel' },
      { text: t('admin.orders.refund'), style: 'destructive', onPress: () => action.run(o.id, async () => { await api.call('POST', `/admin/orders/${o.id}/refund`); await list.reload(); }) },
    ]);
  const fulfil = (o: any, value: string) => action.run(o.id, async () => { await api.call('POST', `/admin/orders/${o.id}/fulfilment`, { fulfilment_status: value }); await list.reload(); });
  return (
    <AdminPage title={t('admin.sections.orders')} intro={t('admin.orders.intro')} loading={list.loading && !list.data} error={list.error ?? action.error}
      onRefresh={list.reload} testID="admin-orders">
      <Chips scroll value={status} onChange={setStatus} options={['', 'paid', 'refund_due', 'pending', 'refunded', 'failed'].map(s => ({ value: s, label: s ? t(`admin.orders.status.${s}`) : t('admin.all') }))} />
      {list.data?.length === 0 ? <AppText muted>{t('admin.none')}</AppText> : null}
      {list.data?.map(o => (
        <Card key={o.id}>
          <Row style={styles.lineRow}>
            <View style={styles.flex}>
              <AppText style={styles.bold}>{o.items.map((i: any) => i.title).join(', ')}</AppText>
              <AppText variant="small" muted>{`${day(o.created_at)} · ${o.kind}`}</AppText>
            </View>
            <AppText style={styles.bold}>{money(o.amount_minor, o.currency)}</AppText>
          </Row>
          <Tag label={t(`admin.orders.status.${o.status}`, { defaultValue: o.status })} tone={o.status === 'paid' ? 'sage' : o.status === 'refund_due' ? 'rose' : 'gold'} />
          {o.shipping ? (
            <>
              <AppText variant="small" muted>{[o.shipping.full_name, o.shipping.line1, o.shipping.city, o.shipping.phone].filter(Boolean).join(', ')}</AppText>
              {o.status === 'paid' ? (
                <Chips value={o.fulfilment_status ?? 'unfulfilled'} onChange={v => fulfil(o, v)}
                  options={['unfulfilled', 'shipped', 'delivered'].map(s => ({ value: s, label: t(`admin.orders.delivery.${s}`) }))} />
              ) : null}
            </>
          ) : null}
          {['paid', 'refund_due'].includes(o.status) ? <Button kind="soft" label={t('admin.orders.refund')} onPress={() => refund(o)} loading={action.busy === o.id} testID={`refund-${o.id}`} /> : null}
        </Card>
      ))}
    </AdminPage>
  );
}

// ---------------------------------------------------------------- moderation

export function AdminModerationScreen() {
  const { t } = useTranslation();
  const { api } = useApp();
  const violations = useLoad(() => api.call<any[]>('GET', '/admin/moderation/violations'), [api]);
  const restrictions = useLoad(() => api.call<any[]>('GET', '/admin/moderation/restrictions'), [api]);
  const testimonials = useLoad(() => api.call<any[]>('GET', '/admin/stylists/testimonials').catch(() => []), [api]);
  const action = useAction();
  const review = (id: string, uphold: boolean) => action.run(id, async () => { await api.call('POST', `/admin/moderation/violations/${id}`, { uphold }); await violations.reload(); });
  const lift = (id: string) => action.run(id, async () => { await api.call('POST', `/admin/moderation/users/${id}/lift`, { note: 'Reviewed in the app' }); await restrictions.reload(); });
  const toggle = (tm: any) => action.run(tm.id, async () => { await api.call('PATCH', `/admin/stylists/testimonials/${tm.id}`, { status: tm.status === 'published' ? 'hidden' : 'published' }); await testimonials.reload(); });
  return (
    <AdminPage title={t('admin.sections.moderation')} intro={t('admin.moderation.intro')} error={violations.error ?? action.error}
      onRefresh={() => { violations.reload(); restrictions.reload(); testimonials.reload(); }} testID="admin-moderation">
      <SectionTitle>{t('admin.moderation.flagged')}</SectionTitle>
      {violations.data?.length === 0 ? <AppText muted>{t('admin.none')}</AppText> : null}
      {violations.data?.map(v => (
        <Card key={v.id}>
          <AppText style={styles.bold}>{v.user.name}</AppText>
          <AppText variant="small" muted>{`${v.user.email} · ${t('admin.moderation.count', { count: v.user_violations })}`}</AppText>
          <View style={styles.quote}><AppText>{v.message}</AppText></View>
          <Row style={styles.tags}>{v.kinds.map((k: string) => <Tag key={k} label={k} tone="rose" />)}</Row>
          <Row style={styles.actions}>
            <View style={styles.flex}><Button kind="soft" label={t('admin.moderation.dismiss')} onPress={() => review(v.id, false)} testID={`dismiss-${v.id}`} /></View>
            <View style={styles.flex}><Button label={t('admin.moderation.uphold')} onPress={() => review(v.id, true)} testID={`uphold-${v.id}`} /></View>
          </Row>
        </Card>
      ))}
      <SectionTitle>{t('admin.moderation.restricted')}</SectionTitle>
      {restrictions.data?.length === 0 ? <AppText muted>{t('admin.none')}</AppText> : null}
      {restrictions.data?.map(r => (
        <Card key={r.user_id}>
          <AppText variant="small" muted>{r.banned_at ? t('admin.moderation.closed', { date: day(r.banned_at) }) : t('admin.moderation.until', { date: day(r.suspended_until) })}</AppText>
          <Button kind="soft" label={t('admin.moderation.lift')} onPress={() => lift(r.user_id)} />
        </Card>
      ))}
      <SectionTitle>{t('stylists.testimonials')}</SectionTitle>
      {testimonials.data?.map(tm => (
        <Card key={tm.id}>
          <Row style={styles.lineRow}>
            <AppText style={[styles.bold, styles.flex]}>{tm.stylist}</AppText>
            <Rating value={tm.rating} count={1} />
          </Row>
          {tm.text ? <AppText>{tm.text}</AppText> : null}
          <Button kind="link" label={tm.status === 'published' ? t('admin.moderation.hide') : t('admin.moderation.publish')} onPress={() => toggle(tm)} />
        </Card>
      ))}
    </AdminPage>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  bold: { fontWeight: '700' },
  tags: { gap: 6, flexWrap: 'wrap' },
  actions: { gap: spacing.sm, alignItems: 'center', flexWrap: 'wrap' },
  doc: { width: '100%', height: 220, borderRadius: radius.md, backgroundColor: '#F3ECEC' },
  line: { borderTopWidth: 1, borderTopColor: '#EFE2E2', paddingTop: spacing.sm, gap: 2 },
  lineRow: { gap: spacing.sm, alignItems: 'center' },
  quote: { backgroundColor: '#FBF1F3', borderRadius: radius.sm, padding: spacing.sm },
});
