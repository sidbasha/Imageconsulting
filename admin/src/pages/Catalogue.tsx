import { useState } from 'react';

import { api, money } from '../api';
import { useI18n } from '../i18n';
import { Bilingual, ErrorNote, Loading, Page, useAction, useData } from '../ui';

type Product = { key: string; kind: string; title: Record<string, string>; price_minor: number; is_free: boolean; is_active: boolean; content_status: string };
type Plan = { key: string; audience: string; title: Record<string, string>; price_minor: number; currency: string; interval: string; grants: string[]; is_active: boolean };

/** Guides, reports, physical items and credits (rows 37-39, 48, 57). Prices need the pricing permission (row 55). */
export function CatalogueProducts() {
  const list = useData(() => api<Product[]>('GET', '/admin/products'));
  return (
    <Page title="Products" intro="Every seeded title and price is a placeholder until the client approves it. Changing a price needs the pricing permission.">
      <ErrorNote error={list.error} />
      <Loading loading={list.loading} />
      {list.data?.map(p => <ProductRow key={p.key} product={p} onSaved={list.reload} />)}
    </Page>
  );
}

function ProductRow({ product, onSaved }: { product: Product; onSaved: () => void }) {
  const { t } = useI18n();
  const [title, setTitle] = useState(product.title);
  const [price, setPrice] = useState((product.price_minor / 100).toFixed(2));
  const [active, setActive] = useState(product.is_active);
  const [approved, setApproved] = useState(product.content_status === 'approved');
  const action = useAction();
  const save = () =>
    action.run('save', async () => {
      const body: any = { title, is_active: active, content_status: approved ? 'approved' : 'draft' };
      const minor = Math.round(Number(price) * 100);
      if (!product.is_free && minor !== product.price_minor) {
        body.price_minor = minor;
      }
      await api('PATCH', `/admin/products/${product.key}`, body);
      onSaved();
    }, t('Saved'));
  return (
    <div className="card">
      <p><code>{product.key}</code> <span className="muted">{product.kind}{product.is_free ? ' · free' : ` · ${money(product.price_minor)}`}</span></p>
      <Bilingual label="Title" value={title} onChange={setTitle} />
      <div className="row">
        {!product.is_free ? <label>Price (AED)<input value={price} onChange={e => setPrice(e.target.value)} inputMode="decimal" data-testid={`price-${product.key}`} /></label> : null}
        <label style={{ flexDirection: 'row' }}><input type="checkbox" checked={active} onChange={e => setActive(e.target.checked)} /> On sale</label>
        <label style={{ flexDirection: 'row' }}><input type="checkbox" checked={approved} onChange={e => setApproved(e.target.checked)} /> Content approved</label>
        <button onClick={save} disabled={action.busy !== null} data-testid={`save-${product.key}`}>{t('Save')}</button>
        {action.done ? <span className="ok">{action.done}</span> : null}
      </div>
      <ErrorNote error={action.error} />
    </div>
  );
}

/** Customer and consultant plans (rows 35, 40, 55). Billing structure is open decision 61. */
export function CataloguePlans() {
  const { t } = useI18n();
  const list = useData(() => api<Plan[]>('GET', '/admin/plans'));
  const action = useAction();
  const [prices, setPrices] = useState<Record<string, string>>({});
  const save = (p: Plan, changes: Record<string, unknown>) =>
    action.run(p.key, async () => {
      await api('PATCH', `/admin/plans/${p.key}`, changes);
      await list.reload();
    }, t('Saved'));
  return (
    <Page title="Plans" intro="Each plan bills its full price once per interval (row 61 is still open).">
      <ErrorNote error={list.error ?? action.error} />
      {action.done ? <p className="ok">{action.done}</p> : null}
      <Loading loading={list.loading} />
      {list.data ? (
        <table>
          <thead><tr><th>Plan</th><th>Audience</th><th>Price</th><th>Interval</th><th>Gives</th><th /></tr></thead>
          <tbody>
            {list.data.map(p => (
              <tr key={p.key}>
                <td>{p.title.en}<br /><code className="muted">{p.key}</code></td>
                <td>{p.audience}</td>
                <td><input value={prices[p.key] ?? (p.price_minor / 100).toFixed(2)} style={{ width: 100 }} onChange={e => setPrices({ ...prices, [p.key]: e.target.value })} /></td>
                <td>{p.interval}</td>
                <td>{p.grants.join(', ')}</td>
                <td className="row">
                  <button onClick={() => save(p, { price_minor: Math.round(Number(prices[p.key] ?? p.price_minor / 100) * 100) })}>{t('Save')}</button>
                  <button className="link" onClick={() => save(p, { is_active: !p.is_active })}>{p.is_active ? 'Withdraw' : 'Offer'}</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : null}
    </Page>
  );
}
