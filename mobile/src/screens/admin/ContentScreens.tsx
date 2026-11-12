/** Staff content and configuration: catalogue (57), plans (55), try-on library (11, 12), retail (36),
 * promotions and vouchers (42, 49-51, 60), rewards (59), settings and countries (3, 52, 61-66). */
import React, { useEffect, useState } from 'react';
import { Image, StyleSheet, Switch, View } from 'react-native';
import { launchImageLibrary } from 'react-native-image-picker';
import { useTranslation } from 'react-i18next';

import { AppText, Button, Card, Chips, ErrorBanner, Row, SectionTitle, Tag, TextField, money } from '../../components/ui';
import { useApp } from '../../contexts/AppContext';
import { colors, radius, spacing } from '../../theme';
import { errorMessage } from '../errorMessage';
import { useLoad } from '../useLoad';
import { AdminPage, day, useAction } from './common';

// ---------------------------------------------------------------- products

export function AdminCatalogueScreen() {
  const { t } = useTranslation();
  const { api, user } = useApp();
  const list = useLoad(() => api.call<any[]>('GET', '/admin/products'), [api]);
  const canPrice = (user?.permissions ?? []).includes('pricing.manage');
  return (
    <AdminPage title={t('admin.sections.catalogue')} intro={t('admin.catalogue.intro')} loading={list.loading && !list.data} error={list.error}
      onRefresh={list.reload} testID="admin-catalogue">
      {list.data?.map(p => <ProductCard key={p.key} product={p} canPrice={canPrice} onSaved={list.reload} />)}
    </AdminPage>
  );
}

function ProductCard({ product, canPrice, onSaved }: { product: any; canPrice: boolean; onSaved: () => void }) {
  const { t, i18n } = useTranslation();
  const { api } = useApp();
  const [price, setPrice] = useState((product.price_minor / 100).toFixed(2));
  const action = useAction();
  const save = (changes: Record<string, unknown>) => action.run('save', async () => { await api.call('PATCH', `/admin/products/${product.key}`, changes); onSaved(); }, t('admin.saved'));
  return (
    <Card>
      <Row style={styles.lineRow}>
        <View style={styles.flex}>
          <AppText style={styles.bold}>{product.title[i18n.language] ?? product.title.en}</AppText>
          <AppText variant="small" muted>{product.kind}</AppText>
        </View>
        <Tag label={product.is_free ? t('library.free') : money(product.price_minor, 'AED')} tone={product.is_free ? 'gold' : 'rose'} />
      </Row>
      <Row style={styles.lineRow}>
        <AppText style={styles.flex}>{t('admin.catalogue.onSale')}</AppText>
        <Switch value={product.is_active} onValueChange={v => { save({ is_active: v }); }} trackColor={{ true: colors.primary }} />
      </Row>
      <Row style={styles.lineRow}>
        <AppText style={styles.flex}>{t('admin.catalogue.approved')}</AppText>
        <Switch value={product.content_status === 'approved'} onValueChange={v => { save({ content_status: v ? 'approved' : 'draft' }); }} trackColor={{ true: colors.primary }} />
      </Row>
      {canPrice && !product.is_free ? (
        <Row style={styles.lineRow}>
          <View style={styles.flex}><TextField label={t('admin.priceAed')} value={price} onChangeText={setPrice} keyboardType="decimal-pad" testID={`price-${product.key}`} /></View>
          <Button kind="soft" label={t('admin.save')} onPress={() => save({ price_minor: Math.round(Number(price) * 100) })} />
        </Row>
      ) : null}
      {action.done ? <AppText variant="small" style={styles.ok}>{action.done}</AppText> : null}
      <ErrorBanner message={action.error ? errorMessage(action.error, t) : null} />
    </Card>
  );
}

// ---------------------------------------------------------------- plans

export function AdminPlansScreen() {
  const { t, i18n } = useTranslation();
  const { api } = useApp();
  const list = useLoad(() => api.call<any[]>('GET', '/admin/plans'), [api]);
  const [prices, setPrices] = useState<Record<string, string>>({});
  const action = useAction();
  const save = (p: any, changes: Record<string, unknown>) => action.run(p.key, async () => { await api.call('PATCH', `/admin/plans/${p.key}`, changes); await list.reload(); }, t('admin.saved'));
  return (
    <AdminPage title={t('admin.sections.plans')} intro={t('admin.plans.intro')} loading={list.loading && !list.data} error={list.error ?? action.error} onRefresh={list.reload}>
      {action.done ? <AppText style={styles.ok}>{action.done}</AppText> : null}
      {list.data?.map(p => (
        <Card key={p.key}>
          <AppText style={styles.bold}>{p.title[i18n.language] ?? p.title.en}</AppText>
          <AppText variant="small" muted>{`${p.audience} · ${t(`plans.per.${p.interval}`, { amount: money(p.price_minor, p.currency) })}`}</AppText>
          <Row style={styles.lineRow}>
            <AppText style={styles.flex}>{t('admin.plans.offered')}</AppText>
            <Switch value={p.is_active} onValueChange={v => { save(p, { is_active: v }); }} trackColor={{ true: colors.primary }} />
          </Row>
          <Row style={styles.lineRow}>
            <View style={styles.flex}><TextField label={t('admin.priceAed')} value={prices[p.key] ?? (p.price_minor / 100).toFixed(2)} keyboardType="decimal-pad"
              onChangeText={v => setPrices({ ...prices, [p.key]: v })} /></View>
            <Button kind="soft" label={t('admin.save')} onPress={() => save(p, { price_minor: Math.round(Number(prices[p.key] ?? p.price_minor / 100) * 100) })} />
          </Row>
        </Card>
      ))}
    </AdminPage>
  );
}

// ---------------------------------------------------------------- try-on library

export function AdminTryOnScreen() {
  const { t, i18n } = useTranslation();
  const { api } = useApp();
  const list = useLoad(() => api.call<any[]>('GET', '/admin/tryon-items'), [api]);
  const [kind, setKind] = useState<string | null>('garment');
  const [titleEn, setTitleEn] = useState('');
  const [titleAr, setTitleAr] = useState('');
  const [licence, setLicence] = useState('');
  const action = useAction();
  const upload = () =>
    action.run('upload', async () => {
      const picked = await launchImageLibrary({ mediaType: 'photo', selectionLimit: 1, maxWidth: 2000, maxHeight: 2000, quality: 0.9 });
      const a = picked.assets?.[0];
      if (!a?.uri) {
        return;
      }
      await api.uploadTryOn({ uri: a.uri, name: a.fileName ?? 'reference.jpg', type: a.type ?? 'image/jpeg' },
        { kind: kind ?? 'garment', title_en: titleEn, title_ar: titleAr, licence });
      setTitleEn('');
      setTitleAr('');
      await list.reload();
    }, t('admin.tryOn.uploaded'));
  return (
    <AdminPage title={t('admin.sections.tryOn')} intro={t('admin.tryOn.intro')} error={list.error} onRefresh={list.reload}>
      <Card>
        <Chips value={kind} onChange={setKind} options={[{ value: 'garment', label: t('admin.tryOn.garment') }, { value: 'hairstyle', label: t('admin.tryOn.hairstyle') }]} />
        <TextField label={t('admin.titleEn')} value={titleEn} onChangeText={setTitleEn} />
        <TextField label={t('admin.titleAr')} value={titleAr} onChangeText={setTitleAr} />
        <TextField label={t('admin.tryOn.licence')} value={licence} onChangeText={setLicence} hint={t('admin.tryOn.licenceHint')} />
        <Button label={t('admin.tryOn.pick')} onPress={() => (titleEn && titleAr && licence.length >= 3 ? upload() : undefined)} loading={action.busy === 'upload'} />
        {action.done ? <AppText style={styles.ok}>{action.done}</AppText> : null}
        <ErrorBanner message={action.error ? errorMessage(action.error, t) : null} />
      </Card>
      {list.data?.map(item => <TryOnCard key={item.id} item={item} language={i18n.language} onChange={list.reload} />)}
    </AdminPage>
  );
}

function TryOnCard({ item, language, onChange }: { item: any; language: string; onChange: () => void }) {
  const { t } = useTranslation();
  const { api } = useApp();
  const [image, setImage] = useState<string | null>(null);
  const action = useAction();
  useEffect(() => {
    api.image(`/admin/tryon-items/${item.id}/image`).then(setImage).catch(() => undefined);
  }, [api, item.id]);
  const patch = (body: Record<string, unknown>) => action.run('patch', async () => { await api.call('PATCH', `/admin/tryon-items/${item.id}`, body); onChange(); });
  return (
    <Card>
      <Row style={styles.lineRow}>
        {image ? <Image source={{ uri: image }} style={styles.cutout} resizeMode="contain" /> : <View style={styles.cutout} />}
        <View style={styles.flex}>
          <AppText style={styles.bold}>{item.title[language] ?? item.title.en}</AppText>
          <AppText variant="small" muted>{`${t(`admin.tryOn.${item.kind}`)} · ${day(item.created_at)}`}</AppText>
          <AppText variant="small" muted numberOfLines={2}>{item.licence}</AppText>
          <Tag label={item.content_status === 'approved' ? t('admin.tryOn.live') : t('admin.tryOn.draft')} tone={item.content_status === 'approved' ? 'sage' : 'gold'} />
        </View>
      </Row>
      <Button kind={item.content_status === 'approved' ? 'soft' : 'primary'} label={item.content_status === 'approved' ? t('admin.tryOn.withdraw') : t('admin.approve')}
        onPress={() => patch({ content_status: item.content_status === 'approved' ? 'draft' : 'approved' })} />
    </Card>
  );
}

// ---------------------------------------------------------------- retail links

export function AdminRetailScreen() {
  const { t, i18n } = useTranslation();
  const { api } = useApp();
  const list = useLoad(() => api.call<any[]>('GET', '/admin/retail-items'), [api]);
  const [form, setForm] = useState({ retailer: '', en: '', ar: '', url: 'https://', price: '', tags: '' });
  const action = useAction();
  const parseTags = (raw: string) => Object.fromEntries(raw.split(';').map(p => p.split(':')).filter(p => p.length === 2 && p[0].trim())
    .map(([k, v]) => [k.trim(), v.split(',').map(x => x.trim()).filter(Boolean)]));
  const add = () => action.run('add', async () => {
    await api.call('POST', '/admin/retail-items', { retailer: form.retailer, title: { en: form.en, ar: form.ar }, url: form.url,
      price_text: form.price || null, tags: parseTags(form.tags) });
    setForm({ retailer: '', en: '', ar: '', url: 'https://', price: '', tags: '' });
    await list.reload();
  }, t('admin.saved'));
  return (
    <AdminPage title={t('admin.sections.retail')} intro={t('admin.retail.intro')} error={list.error} onRefresh={list.reload}>
      <Card>
        <TextField label={t('admin.retail.retailer')} value={form.retailer} onChangeText={v => setForm({ ...form, retailer: v })} />
        <TextField label={t('admin.titleEn')} value={form.en} onChangeText={v => setForm({ ...form, en: v })} />
        <TextField label={t('admin.titleAr')} value={form.ar} onChangeText={v => setForm({ ...form, ar: v })} />
        <TextField label={t('admin.retail.link')} value={form.url} onChangeText={v => setForm({ ...form, url: v })} autoCapitalize="none" keyboardType="url" />
        <TextField label={t('admin.retail.price')} value={form.price} onChangeText={v => setForm({ ...form, price: v })} hint="AED 249" />
        <TextField label={t('admin.retail.matches')} value={form.tags} onChangeText={v => setForm({ ...form, tags: v })} hint="seasonal_color: autumn; body_shape: pear" autoCapitalize="none" />
        <Button label={t('admin.add')} onPress={add} loading={action.busy === 'add'} />
        {action.done ? <AppText style={styles.ok}>{action.done}</AppText> : null}
        <ErrorBanner message={action.error ? errorMessage(action.error, t) : null} />
      </Card>
      {list.data?.map(i => (
        <Card key={i.id}>
          <AppText style={styles.bold}>{i.title[i18n.language] ?? i.title.en}</AppText>
          <AppText variant="small" muted>{`${i.retailer} · ${t('admin.retail.clicks', { count: i.clicks })}`}</AppText>
        </Card>
      ))}
    </AdminPage>
  );
}

// ---------------------------------------------------------------- promotions and vouchers

export function AdminPromotionsScreen() {
  const { t, i18n } = useTranslation();
  const { api } = useApp();
  const campaigns = useLoad(() => api.call<any[]>('GET', '/admin/promotions/campaigns'), [api]);
  const vouchers = useLoad(() => api.call<any[]>('GET', '/admin/promotions/vouchers'), [api]);
  const [v, setV] = useState({ partner: '', en: '', ar: '', code: '', days: '30', max: '' });
  const action = useAction();
  const decide = (c: any, status: string) => action.run(c.id, async () => { await api.call('POST', `/admin/promotions/campaigns/${c.id}/status`, { status }); await campaigns.reload(); });
  const addVoucher = () => action.run('voucher', async () => {
    const now = new Date();
    await api.call('POST', '/admin/promotions/vouchers', { partner_name: v.partner, title: { en: v.en, ar: v.ar }, code: v.code,
      starts_at: now.toISOString(), ends_at: new Date(now.getTime() + Number(v.days || 30) * 86400000).toISOString(), max_claims: v.max ? Number(v.max) : null });
    setV({ partner: '', en: '', ar: '', code: '', days: '30', max: '' });
    await vouchers.reload();
  }, t('admin.saved'));
  return (
    <AdminPage title={t('admin.sections.promotions')} error={campaigns.error ?? action.error} onRefresh={() => { campaigns.reload(); vouchers.reload(); }}>
      <SectionTitle>{t('admin.promotions.campaigns')}</SectionTitle>
      {campaigns.data?.length === 0 ? <AppText muted>{t('admin.none')}</AppText> : null}
      {campaigns.data?.map(c => (
        <Card key={c.id}>
          <Row style={styles.lineRow}>
            <View style={styles.flex}>
              <AppText style={styles.bold}>{c.advertiser}</AppText>
              <AppText variant="small" muted>{`${c.placement} · ${day(c.starts_at)} → ${day(c.ends_at)}`}</AppText>
              <AppText variant="small" muted>{t('admin.promotions.stats', { seen: c.impressions, clicks: c.clicks })}</AppText>
            </View>
            <Tag label={t(`featured.status.${c.status}`, { defaultValue: c.status })} tone={c.status === 'active' ? 'sage' : 'gold'} />
          </Row>
          {c.status === 'pending_review' ? (
            <Row style={styles.actions}>
              <View style={styles.flex}><Button kind="soft" label={t('admin.reject')} onPress={() => decide(c, 'rejected')} /></View>
              <View style={styles.flex}><Button label={t('admin.approve')} onPress={() => decide(c, 'active')} testID={`activate-${c.id}`} /></View>
            </Row>
          ) : c.status === 'active' ? <Button kind="soft" label={t('admin.promotions.stop')} onPress={() => decide(c, 'cancelled')} /> : null}
        </Card>
      ))}
      <SectionTitle>{t('offers.title.vouchers')}</SectionTitle>
      {vouchers.data?.map(x => (
        <Card key={x.id}>
          <AppText style={styles.bold}>{x.title[i18n.language] ?? x.title.en}</AppText>
          <AppText variant="small" muted>{`${x.partner} · ${x.claimed}${x.max_claims ? ` / ${x.max_claims}` : ''} · ${day(x.ends_at)}`}</AppText>
        </Card>
      ))}
      <Card>
        <AppText variant="heading">{t('admin.promotions.newVoucher')}</AppText>
        <TextField label={t('admin.promotions.partner')} value={v.partner} onChangeText={x => setV({ ...v, partner: x })} />
        <TextField label={t('admin.titleEn')} value={v.en} onChangeText={x => setV({ ...v, en: x })} />
        <TextField label={t('admin.titleAr')} value={v.ar} onChangeText={x => setV({ ...v, ar: x })} />
        <TextField label={t('admin.promotions.code')} value={v.code} onChangeText={x => setV({ ...v, code: x })} autoCapitalize="characters" />
        <Row style={styles.actions}>
          <View style={styles.flex}><TextField label={t('admin.promotions.days')} value={v.days} onChangeText={x => setV({ ...v, days: x })} keyboardType="number-pad" /></View>
          <View style={styles.flex}><TextField label={t('admin.promotions.max')} value={v.max} onChangeText={x => setV({ ...v, max: x })} keyboardType="number-pad" /></View>
        </Row>
        <Button label={t('admin.add')} onPress={addVoucher} loading={action.busy === 'voucher'} />
        {action.done ? <AppText style={styles.ok}>{action.done}</AppText> : null}
      </Card>
    </AdminPage>
  );
}

// ---------------------------------------------------------------- rewards

export function AdminRewardsScreen() {
  const { t } = useTranslation();
  const { api } = useApp();
  const rules = useLoad(() => api.call<any[]>('GET', '/admin/rewards/rules'), [api]);
  const [edits, setEdits] = useState<Record<string, string>>({});
  const action = useAction();
  const save = (r: any, changes: Record<string, unknown>) => action.run(r.event, async () => { await api.call('PATCH', `/admin/rewards/rules/${r.event}`, changes); await rules.reload(); }, t('admin.saved'));
  return (
    <AdminPage title={t('admin.sections.rewards')} intro={t('admin.rewards.intro')} error={rules.error ?? action.error} onRefresh={rules.reload}>
      {action.done ? <AppText style={styles.ok}>{action.done}</AppText> : null}
      {rules.data?.map(r => (
        <Card key={r.event}>
          <Row style={styles.lineRow}>
            <AppText style={[styles.bold, styles.flex]}>{t(`admin.rewards.events.${r.event}`, { defaultValue: r.event })}</AppText>
            <Switch value={r.is_active} onValueChange={on => { save(r, { is_active: on }); }} trackColor={{ true: colors.primary }} />
          </Row>
          <Row style={styles.lineRow}>
            <View style={styles.flex}><TextField label={t('admin.rewards.points')} value={edits[r.event] ?? String(r.points)} keyboardType="number-pad"
              onChangeText={x => setEdits({ ...edits, [r.event]: x })} /></View>
            <Button kind="soft" label={t('admin.save')} onPress={() => save(r, { points: Number(edits[r.event] ?? r.points) })} />
          </Row>
        </Card>
      ))}
    </AdminPage>
  );
}

// ---------------------------------------------------------------- settings

export function AdminSettingsScreen() {
  const { t } = useTranslation();
  const { api } = useApp();
  const settings = useLoad(() => api.call<any[]>('GET', '/admin/settings'), [api]);
  const [edits, setEdits] = useState<Record<string, string>>({});
  const action = useAction();
  const show = (v: unknown) => (typeof v === 'object' ? JSON.stringify(v) : String(v));
  const save = (s: any, raw?: string) => action.run(s.key, async () => {
    const text = raw ?? edits[s.key] ?? show(s.value);
    const value = typeof s.value === 'boolean' ? text === 'true' : typeof s.value === 'number' ? Number(text) : typeof s.value === 'object' ? JSON.parse(text) : text;
    await api.call('PUT', `/admin/settings/${s.key}`, { value });
    await settings.reload();
  }, t('admin.saved'));
  return (
    <AdminPage title={t('admin.sections.settings')} intro={t('admin.settings.intro')} error={settings.error ?? action.error} onRefresh={settings.reload}>
      {action.done ? <AppText style={styles.ok}>{action.done}</AppText> : null}
      {settings.data?.map(s => (
        <Card key={s.key}>
          <AppText style={styles.bold}>{t(`admin.settings.names.${s.key.replace(/\./g, '_')}`, { defaultValue: s.key })}</AppText>
          <AppText variant="small" muted>{s.description}</AppText>
          {typeof s.value === 'boolean' ? (
            <Row style={styles.lineRow}>
              <AppText style={styles.flex}>{s.value ? t('admin.on') : t('admin.off')}</AppText>
              <Switch value={s.value} onValueChange={on => { save(s, String(on)); }} trackColor={{ true: colors.primary }} testID={`setting-${s.key}`} />
            </Row>
          ) : (
            <Row style={styles.lineRow}>
              <View style={styles.flex}><TextField label={s.key} value={edits[s.key] ?? show(s.value)} autoCapitalize="none"
                onChangeText={x => setEdits({ ...edits, [s.key]: x })} testID={`setting-${s.key}`} /></View>
              <Button kind="soft" label={t('admin.save')} onPress={() => save(s)} />
            </Row>
          )}
        </Card>
      ))}
    </AdminPage>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  bold: { fontWeight: '700' },
  ok: { color: '#2F6B4F', fontWeight: '600' },
  actions: { gap: spacing.sm, alignItems: 'center' },
  lineRow: { gap: spacing.sm, alignItems: 'center' },
  cutout: { width: 84, height: 104, borderRadius: radius.md, backgroundColor: colors.backgroundDeep },
});
