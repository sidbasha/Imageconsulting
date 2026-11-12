import { useState } from 'react';

import { api, day, money } from '../api';
import { useI18n } from '../i18n';
import { Bilingual, ErrorNote, Loading, Page, useAction, useData } from '../ui';

type Campaign = { id: string; advertiser_type: string; advertiser: string; placement: string; status: string; starts_at: string; ends_at: string;
  impressions: number; clicks: number; price_minor: number; radius_km: number | null };
type Voucher = { id: string; partner: string; title: Record<string, string>; claimed: number; max_claims: number | null; starts_at: string; ends_at: string };

const inDays = (n: number) => new Date(Date.now() + n * 86400000).toISOString().slice(0, 16);

/** Paid stylist placement, brand campaigns with optional area targeting, vouchers (rows 42, 49-51, 60). */
export function Promotions() {
  const { t } = useI18n();
  const campaigns = useData(() => api<Campaign[]>('GET', '/admin/promotions/campaigns'));
  const vouchers = useData(() => api<Voucher[]>('GET', '/admin/promotions/vouchers'));
  const action = useAction();
  const [c, setC] = useState({ advertiser_name: '', placement: 'home_banner', title: { en: '', ar: '' }, body: { en: '', ar: '' },
    target_url: '', starts_at: inDays(0), ends_at: inDays(14), latitude: '', longitude: '', radius_km: '' });
  const [v, setV] = useState({ partner_name: '', title: { en: '', ar: '' }, terms: { en: '', ar: '' }, code: '', starts_at: inDays(0), ends_at: inDays(30), max_claims: '' });

  const decide = (x: Campaign, status: string) =>
    action.run(x.id, async () => {
      await api('POST', `/admin/promotions/campaigns/${x.id}/status`, { status });
      await campaigns.reload();
    });
  const createCampaign = () =>
    action.run('campaign', async () => {
      const geo = c.radius_km ? { latitude: Number(c.latitude), longitude: Number(c.longitude), radius_km: Number(c.radius_km) } : {};
      await api('POST', '/admin/promotions/campaigns', {
        advertiser_name: c.advertiser_name, placement: c.placement, title: c.title, body: c.body, target_url: c.target_url || null,
        starts_at: new Date(c.starts_at).toISOString(), ends_at: new Date(c.ends_at).toISOString(), ...geo,
      });
      await campaigns.reload();
    }, t('Saved'));
  const createVoucher = () =>
    action.run('voucher', async () => {
      await api('POST', '/admin/promotions/vouchers', {
        partner_name: v.partner_name, title: v.title, terms: v.terms, code: v.code, starts_at: new Date(v.starts_at).toISOString(),
        ends_at: new Date(v.ends_at).toISOString(), max_claims: v.max_claims ? Number(v.max_claims) : null,
      });
      await vouchers.reload();
    }, t('Saved'));

  return (
    <Page title="Promotions">
      <ErrorNote error={campaigns.error ?? vouchers.error ?? action.error} />
      {action.done ? <p className="ok">{action.done}</p> : null}
      <h2>Campaigns</h2>
      <Loading loading={campaigns.loading} empty={campaigns.data?.length === 0} />
      {campaigns.data?.length ? (
        <div className="table-wrap">
          <table>
            <thead><tr><th>Advertiser</th><th>Where</th><th>When</th><th>{t('Status')}</th><th>Seen / clicked</th><th /></tr></thead>
            <tbody>
              {campaigns.data.map(x => (
                <tr key={x.id}>
                  <td>{x.advertiser}<br /><span className="muted">{x.advertiser_type}{x.price_minor ? ` · ${money(x.price_minor)}` : ''}</span></td>
                  <td>{x.placement}{x.radius_km ? ` · ${x.radius_km} km` : ''}</td>
                  <td>{day(x.starts_at)} → {day(x.ends_at)}</td>
                  <td>{x.status}</td>
                  <td>{x.impressions} / {x.clicks}</td>
                  <td className="row">
                    {x.status === 'pending_review' ? <button onClick={() => decide(x, 'active')} data-testid={`activate-${x.id}`}>{t('Approve')}</button> : null}
                    {['pending_review', 'active'].includes(x.status) ? <button className="link" onClick={() => decide(x, x.status === 'active' ? 'cancelled' : 'rejected')}>{x.status === 'active' ? 'Stop' : t('Reject')}</button> : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
      <div className="card">
        <h2>New brand campaign</h2>
        <p className="muted">Sold and invoiced by the client's team; entered here to run.</p>
        <div className="row">
          <label>Advertiser<input value={c.advertiser_name} onChange={e => setC({ ...c, advertiser_name: e.target.value })} /></label>
          <label>Placement<select value={c.placement} onChange={e => setC({ ...c, placement: e.target.value })}><option>home_banner</option><option>offers</option></select></label>
          <label>Link<input value={c.target_url} onChange={e => setC({ ...c, target_url: e.target.value })} placeholder="https://" dir="ltr" /></label>
        </div>
        <Bilingual label="Headline" value={c.title} onChange={title => setC({ ...c, title })} />
        <Bilingual label="Text" value={c.body} onChange={body => setC({ ...c, body })} />
        <div className="row">
          <label>Starts<input type="datetime-local" value={c.starts_at} onChange={e => setC({ ...c, starts_at: e.target.value })} /></label>
          <label>Ends<input type="datetime-local" value={c.ends_at} onChange={e => setC({ ...c, ends_at: e.target.value })} /></label>
          <label>Latitude<input value={c.latitude} onChange={e => setC({ ...c, latitude: e.target.value })} style={{ width: 110 }} /></label>
          <label>Longitude<input value={c.longitude} onChange={e => setC({ ...c, longitude: e.target.value })} style={{ width: 110 }} /></label>
          <label>Radius km (empty = everywhere)<input value={c.radius_km} onChange={e => setC({ ...c, radius_km: e.target.value })} style={{ width: 110 }} /></label>
        </div>
        <button onClick={createCampaign} disabled={!c.advertiser_name || !c.title.en}>{t('Create')}</button>
      </div>

      <h2>{t('Vouchers')}</h2>
      {vouchers.data?.length ? (
        <table>
          <thead><tr><th>Partner</th><th>Offer</th><th>Claimed</th><th>Until</th></tr></thead>
          <tbody>
            {vouchers.data.map(x => (
              <tr key={x.id}><td>{x.partner}</td><td>{x.title.en}</td><td>{x.claimed}{x.max_claims ? ` / ${x.max_claims}` : ''}</td><td>{day(x.ends_at)}</td></tr>
            ))}
          </tbody>
        </table>
      ) : <Loading loading={vouchers.loading} empty />}
      <div className="card">
        <div className="row">
          <label>Partner<input value={v.partner_name} onChange={e => setV({ ...v, partner_name: e.target.value })} /></label>
          <label>Code<input value={v.code} onChange={e => setV({ ...v, code: e.target.value })} dir="ltr" /></label>
          <label>Max claims<input value={v.max_claims} onChange={e => setV({ ...v, max_claims: e.target.value })} style={{ width: 100 }} /></label>
        </div>
        <Bilingual label="Offer" value={v.title} onChange={title => setV({ ...v, title })} />
        <Bilingual label="Terms" value={v.terms} onChange={terms => setV({ ...v, terms })} />
        <div className="row">
          <label>Starts<input type="datetime-local" value={v.starts_at} onChange={e => setV({ ...v, starts_at: e.target.value })} /></label>
          <label>Ends<input type="datetime-local" value={v.ends_at} onChange={e => setV({ ...v, ends_at: e.target.value })} /></label>
        </div>
        <button onClick={createVoucher} disabled={!v.partner_name || v.code.length < 3 || !v.title.en}>{t('Create')}</button>
      </div>
    </Page>
  );
}
