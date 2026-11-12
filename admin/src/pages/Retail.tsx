import { useState } from 'react';

import { api } from '../api';
import { useI18n } from '../i18n';
import { Bilingual, ErrorNote, Loading, Page, useAction, useData } from '../ui';

type Item = { id: string; retailer: string; title: Record<string, string>; url: string; category: string; tags: Record<string, string[]>; is_active: boolean; clicks: number };
const EMPTY = { retailer: '', title: { en: '', ar: '' }, url: 'https://', image_url: '', price_text: '', category: 'outfits', tags: '' };

/**
 * Retailer links (row 36). Tags match results, e.g.
 * "seasonal_color: autumn, winter; body_shape: pear; style: classic".
 */
export function Retail() {
  const { t } = useI18n();
  const list = useData(() => api<Item[]>('GET', '/admin/retail-items'));
  const [form, setForm] = useState({ ...EMPTY });
  const [editing, setEditing] = useState<string | null>(null);
  const action = useAction();

  const parseTags = (raw: string) =>
    Object.fromEntries(raw.split(';').map(part => part.split(':')).filter(p => p.length === 2 && p[0].trim())
      .map(([k, v]) => [k.trim(), v.split(',').map(x => x.trim()).filter(Boolean)]));
  const showTags = (tags: Record<string, string[]>) => Object.entries(tags).map(([k, v]) => `${k}: ${v.join(', ')}`).join('; ');

  const save = () =>
    action.run('save', async () => {
      const body = { ...form, image_url: form.image_url || null, price_text: form.price_text || null, tags: parseTags(form.tags), is_active: true };
      await api(editing ? 'PUT' : 'POST', editing ? `/admin/retail-items/${editing}` : '/admin/retail-items', body);
      setForm({ ...EMPTY });
      setEditing(null);
      await list.reload();
    }, t('Saved'));

  return (
    <Page title="Retail links" intro="No items are seeded: the client supplies retailers and products. Links must be https.">
      <div className="card">
        <label>Retailer<input value={form.retailer} onChange={e => setForm({ ...form, retailer: e.target.value })} data-testid="retailer" /></label>
        <Bilingual label="Title" value={form.title} onChange={title => setForm({ ...form, title })} />
        <label>Link<input value={form.url} onChange={e => setForm({ ...form, url: e.target.value })} dir="ltr" data-testid="retail-url" /></label>
        <label>Image link (optional)<input value={form.image_url} onChange={e => setForm({ ...form, image_url: e.target.value })} dir="ltr" /></label>
        <div className="row">
          <label>Price text<input value={form.price_text} onChange={e => setForm({ ...form, price_text: e.target.value })} placeholder="AED 249" /></label>
          <label>Category<select value={form.category} onChange={e => setForm({ ...form, category: e.target.value })}>
            {['outfits', 'eyewear', 'hair', 'makeup', 'accessories'].map(c => <option key={c}>{c}</option>)}</select></label>
        </div>
        <label>Matches<input value={form.tags} onChange={e => setForm({ ...form, tags: e.target.value })} placeholder="seasonal_color: autumn; body_shape: pear" dir="ltr" /></label>
        <div className="row">
          <button onClick={save} disabled={action.busy !== null} data-testid="save-retail">{editing ? t('Save') : t('Create')}</button>
          {editing ? <button className="link" onClick={() => { setEditing(null); setForm({ ...EMPTY }); }}>{t('Cancel')}</button> : null}
          {action.done ? <span className="ok">{action.done}</span> : null}
        </div>
        <ErrorNote error={action.error} />
      </div>
      <ErrorNote error={list.error} />
      <Loading loading={list.loading} empty={list.data?.length === 0} />
      {list.data?.length ? (
        <table>
          <thead><tr><th>Item</th><th>Category</th><th>Matches</th><th>Clicks</th><th /></tr></thead>
          <tbody>
            {list.data.map(i => (
              <tr key={i.id}>
                <td>{i.title.en} <span className="muted">· {i.retailer}</span></td><td>{i.category}</td><td>{showTags(i.tags)}</td><td>{i.clicks}</td>
                <td><button className="link" onClick={() => { setEditing(i.id); setForm({ ...EMPTY, ...i, image_url: '', price_text: '', tags: showTags(i.tags) } as any); }}>Edit</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : null}
    </Page>
  );
}
