import { useState } from 'react';

import { api, day } from '../api';
import { useI18n } from '../i18n';
import { ErrorNote, Loading, Page, useAction, useData } from '../ui';

const BASE = '/admin/phase-management';

type Feature = { key: string; name: string; phase: string; switch_on: boolean; available: boolean; is_enhancement: boolean; source_row: number; requires: string[] };
type State = { release_version: number; phases: { key: string; name: string; enabled: boolean }[]; features: Feature[] };
type Release = { id: string; version: number; status: string; note: string; activate_at: string | null; activated_at: string | null; created_at: string };

/**
 * Release control (Super Admin only). Changes are staged here, checked by the
 * server (dependencies), and applied now or at a scheduled time. Every release
 * is kept and any earlier one can be restored.
 */
export function Releases() {
  const { t } = useI18n();
  const state = useData(() => api<State>('GET', `${BASE}/state`));
  const releases = useData(() => api<Release[]>('GET', `${BASE}/releases`));
  const [phases, setPhases] = useState<Record<string, boolean>>({});
  const [features, setFeatures] = useState<Record<string, boolean>>({});
  const [note, setNote] = useState('');
  const [when, setWhen] = useState('');
  const [check, setCheck] = useState<any>(null);
  const action = useAction();

  const changes = { phases, features };
  const staged = Object.keys(phases).length + Object.keys(features).length;
  const reset = () => {
    setPhases({});
    setFeatures({});
    setCheck(null);
    setNote('');
    setWhen('');
  };
  const refresh = async () => {
    await Promise.all([state.reload(), releases.reload()]);
  };

  const validate = () => action.run('validate', async () => setCheck(await api('POST', `${BASE}/releases/validate`, changes)));
  const apply = () =>
    action.run('apply', async () => {
      const body: any = { ...changes, note };
      if (when) {
        body.activate_at = new Date(when).toISOString();
      }
      await api('POST', `${BASE}/releases`, body);
      reset();
      await refresh();
    }, t('Saved'));
  const rollback = (r: Release) =>
    action.run(r.id, async () => {
      await api('POST', `${BASE}/releases/${r.id}/rollback`, { note: `Restore release ${r.version}` });
      await refresh();
    });
  const cancel = (r: Release) =>
    action.run(r.id, async () => {
      await api('POST', `${BASE}/releases/${r.id}/cancel`);
      await refresh();
    });

  const s = state.data;
  return (
    <Page title="Releases" intro={s ? `Active release v${s.release_version}. Stage changes, check them, then release now or at a set time.` : undefined}>
      <ErrorNote error={state.error ?? action.error} />
      {action.done ? <p className="ok">{action.done}</p> : null}
      <Loading loading={state.loading && !s} />
      {s ? (
        <>
          <h2>Phases</h2>
          <div className="row">
            {s.phases.map(p => {
              const value = phases[p.key] ?? p.enabled;
              return (
                <label key={p.key} className="card" style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
                  <input type="checkbox" checked={value} data-testid={`phase-${p.key}`}
                    onChange={e => setPhases(old => {
                      const next = { ...old };
                      if (e.target.checked === p.enabled) delete next[p.key];
                      else next[p.key] = e.target.checked;
                      return next;
                    })} />
                  {p.name}
                </label>
              );
            })}
          </div>
          <h2>Features</h2>
          <div className="table-wrap">
            <table>
              <thead><tr><th>Row</th><th>Feature</th><th>Phase</th><th>Switch</th><th>Live</th><th>Needs</th></tr></thead>
              <tbody>
                {s.features.map(f => {
                  const value = features[f.key] ?? f.switch_on;
                  return (
                    <tr key={f.key}>
                      <td>{f.source_row}</td>
                      <td>{f.name}{f.is_enhancement ? <span className="muted"> (enhancement)</span> : null}<br /><code className="muted">{f.key}</code></td>
                      <td>{f.phase}</td>
                      <td>
                        <input type="checkbox" checked={value} data-testid={`feature-${f.key}`} aria-label={f.key}
                          onChange={e => setFeatures(old => {
                            const next = { ...old };
                            if (e.target.checked === f.switch_on) delete next[f.key];
                            else next[f.key] = e.target.checked;
                            return next;
                          })} />
                      </td>
                      <td>{f.available ? <span className="pill on">on</span> : <span className="pill">off</span>}</td>
                      <td className="muted">{f.requires.join(', ')}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <div className="card" style={{ marginTop: 16 }}>
            <p>{staged ? `${staged} change(s) staged.` : 'No changes staged.'}</p>
            <label>{t('Note')}<input value={note} onChange={e => setNote(e.target.value)} data-testid="release-note" placeholder="Why this release is made" /></label>
            <label>Activate at (empty = now)<input type="datetime-local" value={when} onChange={e => setWhen(e.target.value)} /></label>
            <div className="row">
              <button disabled={!staged || action.busy !== null} onClick={validate} data-testid="validate">Check</button>
              <button disabled={!staged || note.trim().length < 3 || action.busy !== null} onClick={apply} data-testid="apply">Release</button>
              <button className="link" onClick={reset}>{t('Cancel')}</button>
            </div>
            {check ? (
              <div data-testid="check-result">
                {check.violations.length ? (
                  <p className="error">Blocked by dependencies: {check.violations.map((v: any) => `${v.feature} needs ${v.requires}`).join('; ')}</p>
                ) : (
                  <p className="ok">No dependency problems.</p>
                )}
                {check.would_enable.length ? <p>Turns on: {check.would_enable.join(', ')}</p> : null}
                {check.would_disable.length ? <p>Turns off: {check.would_disable.join(', ')}</p> : null}
              </div>
            ) : null}
          </div>
        </>
      ) : null}
      <h2>History</h2>
      <div className="table-wrap">
        <table>
          <thead><tr><th>Version</th><th>{t('Status')}</th><th>{t('Note')}</th><th>Activated</th><th /></tr></thead>
          <tbody>
            {(releases.data ?? []).map(r => (
              <tr key={r.id}>
                <td>v{r.version}</td>
                <td>{r.status}{r.activate_at && r.status === 'scheduled' ? ` (${day(r.activate_at)})` : ''}</td>
                <td>{r.note}</td>
                <td>{day(r.activated_at)}</td>
                <td>
                  {r.status === 'scheduled' ? <button className="link" onClick={() => cancel(r)}>{t('Cancel')}</button> : null}
                  {r.status === 'superseded' ? (
                    <button className="link" onClick={() => rollback(r)} data-testid={`restore-${r.version}`}>Restore</button>
                  ) : null}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Page>
  );
}
