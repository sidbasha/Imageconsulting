import { useState } from 'react';

import { api } from '../api';
import { useI18n } from '../i18n';
import { ErrorNote, Loading, Page, useAction, useData } from '../ui';

type Rule = { event: string; points: number; max_per_day: number | null; is_active: boolean };
type Option = { key: string; title: Record<string, string>; points_cost: number; is_active: boolean };

/** Points rules and redemption options (rows 43, 44, 59). Points per AED spent is in Settings. */
export function Rewards() {
  const { t } = useI18n();
  const rules = useData(() => api<Rule[]>('GET', '/admin/rewards/rules'));
  const options = useData(() => api<Option[]>('GET', '/admin/rewards/options'));
  const [edits, setEdits] = useState<Record<string, string>>({});
  const [userId, setUserId] = useState('');
  const [delta, setDelta] = useState('');
  const [reason, setReason] = useState('');
  const action = useAction();

  const saveRule = (r: Rule, changes: Partial<Rule>) =>
    action.run(r.event, async () => {
      await api('PATCH', `/admin/rewards/rules/${r.event}`, changes);
      await rules.reload();
    }, t('Saved'));
  const saveOption = (o: Option, changes: Partial<Option>) =>
    action.run(o.key, async () => {
      await api('PATCH', `/admin/rewards/options/${o.key}`, changes);
      await options.reload();
    }, t('Saved'));
  const adjust = () =>
    action.run('adjust', async () => {
      const r = await api<{ balance: number }>('POST', `/admin/rewards/users/${userId}/adjust`, { delta: Number(delta), reason });
      setDelta('');
      return r;
    }, 'Adjusted.');

  return (
    <Page title="Rewards" intro="Draft rules; set real values before launch.">
      <ErrorNote error={rules.error ?? options.error ?? action.error} />
      {action.done ? <p className="ok">{action.done}</p> : null}
      <h2>Earning</h2>
      <Loading loading={rules.loading} />
      {rules.data ? (
        <table>
          <thead><tr><th>Event</th><th>Points</th><th>Per day</th><th>On</th><th /></tr></thead>
          <tbody>
            {rules.data.map(r => (
              <tr key={r.event}>
                <td>{r.event}</td>
                <td><input style={{ width: 90 }} value={edits[r.event] ?? String(r.points)} onChange={e => setEdits({ ...edits, [r.event]: e.target.value })} data-testid={`points-${r.event}`} /></td>
                <td>{r.max_per_day ?? '—'}</td>
                <td><input type="checkbox" checked={r.is_active} onChange={e => saveRule(r, { is_active: e.target.checked })} /></td>
                <td><button onClick={() => saveRule(r, { points: Number(edits[r.event] ?? r.points) })} data-testid={`save-${r.event}`}>{t('Save')}</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : null}
      <h2>Redemption</h2>
      {options.data?.map(o => (
        <div key={o.key} className="card row">
          <strong>{o.title.en}</strong>
          <label>Cost<input style={{ width: 100 }} value={edits[o.key] ?? String(o.points_cost)} onChange={e => setEdits({ ...edits, [o.key]: e.target.value })} /></label>
          <button onClick={() => saveOption(o, { points_cost: Number(edits[o.key] ?? o.points_cost) })}>{t('Save')}</button>
          <button className="link" onClick={() => saveOption(o, { is_active: !o.is_active })}>{o.is_active ? 'Withdraw' : 'Offer'}</button>
        </div>
      ))}
      <h2>Adjust a user's points</h2>
      <div className="card row">
        <label>User id<input value={userId} onChange={e => setUserId(e.target.value)} dir="ltr" /></label>
        <label>Points (+/−)<input value={delta} onChange={e => setDelta(e.target.value)} style={{ width: 100 }} /></label>
        <label>Reason<input value={reason} onChange={e => setReason(e.target.value)} /></label>
        <button onClick={adjust} disabled={!userId || !delta || reason.length < 3}>Apply</button>
      </div>
    </Page>
  );
}
