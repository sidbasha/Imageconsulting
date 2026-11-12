import { useState } from 'react';

import { api, day, money } from '../api';
import { useI18n } from '../i18n';
import { ErrorNote, Loading, Page, useAction, useData } from '../ui';

type Order = { id: string; kind: string; status: string; amount_minor: number; currency: string; items: { title: string; quantity: number }[];
  created_at: string; paid_at: string | null; fulfilment_status: string | null; shipping: Record<string, string> | null; user_id: string };

/** Orders, refunds and physical deliveries (rows 41, 48). */
export function Orders() {
  const { t } = useI18n();
  const [status, setStatus] = useState('');
  const list = useData(() => api<Order[]>('GET', `/admin/orders${status ? `?status_filter=${status}` : ''}`), [status]);
  const action = useAction();
  const refund = (o: Order) => {
    if (!window.confirm(`Refund ${money(o.amount_minor, o.currency)}? Anything the order gave is taken back.`)) {
      return;
    }
    action.run(o.id, async () => {
      await api('POST', `/admin/orders/${o.id}/refund`);
      await list.reload();
    });
  };
  const fulfil = (o: Order, fulfilment_status: string) =>
    action.run(o.id, async () => {
      await api('POST', `/admin/orders/${o.id}/fulfilment`, { fulfilment_status });
      await list.reload();
    });
  return (
    <Page title="Orders" intro="Payments run through the sandbox gateway until a real one is connected.">
      <label style={{ maxWidth: 240 }}>{t('Status')}
        <select value={status} onChange={e => setStatus(e.target.value)} data-testid="order-filter">
          {['', 'pending', 'paid', 'refund_due', 'refunded', 'failed'].map(s => <option key={s} value={s}>{s || 'all'}</option>)}
        </select>
      </label>
      <ErrorNote error={list.error ?? action.error} />
      <Loading loading={list.loading} empty={list.data?.length === 0} />
      {list.data?.length ? (
        <div className="table-wrap">
          <table>
            <thead><tr><th>Date</th><th>Items</th><th>Amount</th><th>{t('Status')}</th><th>Delivery</th><th /></tr></thead>
            <tbody>
              {list.data.map(o => (
                <tr key={o.id}>
                  <td>{day(o.created_at)}</td>
                  <td>{o.items.map(i => `${i.title}${i.quantity > 1 ? ` ×${i.quantity}` : ''}`).join(', ')}<br /><span className="muted">{o.kind}</span></td>
                  <td>{money(o.amount_minor, o.currency)}</td>
                  <td>{o.status}</td>
                  <td>
                    {o.shipping ? (
                      <>
                        <span className="muted">{[o.shipping.full_name, o.shipping.line1, o.shipping.city, o.shipping.phone].filter(Boolean).join(', ')}</span><br />
                        <select value={o.fulfilment_status ?? 'unfulfilled'} disabled={o.status !== 'paid'} onChange={e => fulfil(o, e.target.value)}>
                          {['unfulfilled', 'shipped', 'delivered'].map(s => <option key={s}>{s}</option>)}
                        </select>
                      </>
                    ) : null}
                  </td>
                  <td>
                    {['paid', 'refund_due'].includes(o.status) ? (
                      <button className="danger" onClick={() => refund(o)} disabled={action.busy === o.id} data-testid={`refund-${o.id}`}>Refund</button>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </Page>
  );
}
