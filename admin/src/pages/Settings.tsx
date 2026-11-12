import { useState } from 'react';

import { api } from '../api';
import { useI18n } from '../i18n';
import { ErrorNote, Loading, Page, useAction, useData } from '../ui';

type Setting = { key: string; value: unknown; description: string };
type Country = { code: string; name: string; currency: string };

/** Policy values awaiting client decisions (rows 33, 61-66) and markets (rows 3, 52). */
export function Settings() {
  const { t } = useI18n();
  const settings = useData(() => api<Setting[]>('GET', '/admin/settings'));
  const countries = useData(() => api<Country[]>('GET', '/countries'));
  const [edits, setEdits] = useState<Record<string, string>>({});
  const [code, setCode] = useState('MY');
  const action = useAction();

  const show = (v: unknown) => (typeof v === 'object' ? JSON.stringify(v) : String(v));
  const parse = (raw: string, current: unknown) => {
    if (typeof current === 'boolean') return raw === 'true';
    if (typeof current === 'number') return Number(raw);
    if (typeof current === 'object') return JSON.parse(raw);
    return raw;
  };
  const save = (s: Setting) =>
    action.run(s.key, async () => {
      await api('PUT', `/admin/settings/${s.key}`, { value: parse(edits[s.key] ?? show(s.value), s.value) });
      await settings.reload();
    }, `${s.key}: ${t('Saved')}`);
  const setCountry = (enabled: boolean) =>
    action.run('country', async () => {
      await api('PUT', `/admin/countries/${code}`, { is_enabled: enabled });
      await countries.reload();
    }, t('Saved'));

  return (
    <Page title="Settings" intro="Each value stands in for a decision the client has not made yet. Changes apply immediately, without a release.">
      <ErrorNote error={settings.error ?? action.error} />
      {action.done ? <p className="ok">{action.done}</p> : null}
      <Loading loading={settings.loading} />
      {settings.data ? (
        <table>
          <thead><tr><th>Setting</th><th>Value</th><th /></tr></thead>
          <tbody>
            {settings.data.map(s => (
              <tr key={s.key}>
                <td><code>{s.key}</code><br /><span className="muted">{s.description}</span></td>
                <td>
                  {typeof s.value === 'boolean' ? (
                    <select value={edits[s.key] ?? show(s.value)} onChange={e => setEdits({ ...edits, [s.key]: e.target.value })}><option>true</option><option>false</option></select>
                  ) : (
                    <input value={edits[s.key] ?? show(s.value)} onChange={e => setEdits({ ...edits, [s.key]: e.target.value })} dir="ltr" data-testid={`setting-${s.key}`} />
                  )}
                </td>
                <td><button onClick={() => save(s)} data-testid={`save-${s.key}`}>{t('Save')}</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : null}
      <h2>{t('Countries')}</h2>
      <p className="muted">Open now: {(countries.data ?? []).map(c => c.name).join(', ')}. Other enabled markets appear only once international expansion is released.</p>
      <div className="card row">
        <select value={code} onChange={e => setCode(e.target.value)}>{['MY', 'SG', 'AU'].map(c => <option key={c}>{c}</option>)}</select>
        <button onClick={() => setCountry(true)}>Enable</button>
        <button className="link" onClick={() => setCountry(false)}>Disable</button>
      </div>
    </Page>
  );
}
