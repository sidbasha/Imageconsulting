import { useState } from 'react';

import { api, fileUrl } from '../api';
import { useI18n } from '../i18n';
import { ErrorNote, Loading, Page, useAction, useData } from '../ui';

type Credential = { id: string; kind: string; title: string; status: string; note: string | null };
type Application = { id: string; display_name: string; bio: string; city: string | null; years_experience: number | null;
  business_license_no: string | null; status: string; review_note: string | null; credentials: Credential[] };

/** Stylist applications and credential review (rows 15-17, 53, 54). */
export function Stylists() {
  const { t } = useI18n();
  const [status, setStatus] = useState('submitted');
  const list = useData(() => api<Application[]>('GET', `/admin/stylists?status_filter=${status}`), [status]);
  return (
    <Page title="Stylists" intro="Accept at least one credential before approving. Approved stylists can offer services once their membership is paid.">
      <label style={{ maxWidth: 240 }}>{t('Status')}
        <select value={status} onChange={e => setStatus(e.target.value)}>
          {['submitted', 'approved', 'rejected', 'suspended', 'draft'].map(s => <option key={s} value={s}>{s}</option>)}
        </select>
      </label>
      <ErrorNote error={list.error} />
      <Loading loading={list.loading} empty={list.data?.length === 0} />
      {list.data?.map(a => <ApplicationCard key={a.id} application={a} onChange={list.reload} />)}
    </Page>
  );
}

function ApplicationCard({ application: a, onChange }: { application: Application; onChange: () => void }) {
  const { t } = useI18n();
  const [note, setNote] = useState('');
  const action = useAction();
  const open = (c: Credential) => action.run(c.id, async () => window.open(await fileUrl(`/admin/stylists/credentials/${c.id}/file`), '_blank'));
  const review = (c: Credential, approve: boolean) =>
    action.run(c.id, async () => {
      await api('POST', `/admin/stylists/credentials/${c.id}/review`, { approve });
      onChange();
    });
  const decide = (approve: boolean) =>
    action.run('decide', async () => {
      await api('POST', `/admin/stylists/${a.id}/decision`, { approve, note: note || null });
      onChange();
    });
  return (
    <div className="card" data-testid={`application-${a.display_name}`}>
      <p><strong>{a.display_name}</strong> <span className="muted">{a.city} · {a.status}{a.years_experience !== null ? ` · ${a.years_experience} years` : ''}{a.business_license_no ? ` · licence ${a.business_license_no}` : ''}</span></p>
      <p>{a.bio}</p>
      <table>
        <thead><tr><th>Credential</th><th>Kind</th><th>{t('Status')}</th><th /></tr></thead>
        <tbody>
          {a.credentials.map(c => (
            <tr key={c.id}>
              <td>{c.title}</td><td>{c.kind}</td><td>{c.status}</td>
              <td className="row">
                <button className="link" onClick={() => open(c)}>{t('Open')}</button>
                <button className="link" onClick={() => review(c, true)} data-testid={`accept-${c.id}`}>Accept</button>
                <button className="link" onClick={() => review(c, false)}>{t('Reject')}</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <label>{t('Note')}<input value={note} onChange={e => setNote(e.target.value)} placeholder="Shown to the applicant" /></label>
      <div className="row">
        <button onClick={() => decide(true)} disabled={action.busy !== null} data-testid={`approve-${a.display_name}`}>{t('Approve')}</button>
        <button className="danger" onClick={() => decide(false)} disabled={action.busy !== null}>{a.status === 'approved' ? 'Suspend' : t('Reject')}</button>
      </div>
      <ErrorNote error={action.error} />
    </div>
  );
}
