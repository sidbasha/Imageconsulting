import { useState } from 'react';

import { api, day, fileUrl } from '../api';
import { useI18n } from '../i18n';
import { ErrorNote, Loading, Page, useAction, useData } from '../ui';

type Pending = { id: string; user_id: string; full_name: string; email: string; documents: number; created_at: string };
type Queue = { user_id: string; full_name: string; email: string; status: string; reasons: string[]; identity_status: string };

/** Eligibility approvals and identity document review (rows 1, 2, 53). */
export function Users() {
  const { t } = useI18n();
  const [status, setStatus] = useState('pending_review');
  const queue = useData(() => api<Queue[]>('GET', `/admin/eligibility?status_filter=${status}`), [status]);
  const pending = useData(() => api<Pending[]>('GET', '/admin/identity/pending'));
  const action = useAction();

  const decide = (userId: string, approve: boolean) =>
    action.run(userId, async () => {
      await api('POST', `/admin/eligibility/${userId}`, { approve });
      await queue.reload();
    });

  return (
    <Page title="Users" intro="Customers held for review, and identity documents waiting to be checked.">
      <ErrorNote error={queue.error ?? pending.error ?? action.error} />
      <h2>Eligibility</h2>
      <label style={{ maxWidth: 240 }}>{t('Status')}
        <select value={status} onChange={e => setStatus(e.target.value)} data-testid="eligibility-filter">
          {['pending_review', 'ineligible', 'incomplete', 'eligible'].map(s => <option key={s} value={s}>{s}</option>)}
        </select>
      </label>
      <Loading loading={queue.loading} empty={queue.data?.length === 0} />
      {queue.data?.length ? (
        <table>
          <thead><tr><th>Name</th><th>{t('Email')}</th><th>Reasons</th><th>Identity</th><th /></tr></thead>
          <tbody>
            {queue.data.map(q => (
              <tr key={q.user_id}>
                <td>{q.full_name}</td><td>{q.email}</td><td>{q.reasons.join(', ')}</td><td>{q.identity_status}</td>
                <td className="row">
                  <button onClick={() => decide(q.user_id, true)} disabled={action.busy === q.user_id} data-testid={`approve-${q.email}`}>{t('Approve')}</button>
                  <button className="danger" onClick={() => decide(q.user_id, false)} disabled={action.busy === q.user_id}>{t('Reject')}</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : null}

      <h2>Identity documents</h2>
      <p className="muted">Read the date of birth and gender off the document. Images are deleted once reviewed (setting identity.delete_documents_after_review).</p>
      <Loading loading={pending.loading} empty={pending.data?.length === 0} />
      {pending.data?.map(p => <DocumentReview key={p.id} item={p} onDone={pending.reload} />)}
    </Page>
  );
}

function DocumentReview({ item, onDone }: { item: Pending; onDone: () => void }) {
  const { t } = useI18n();
  const [images, setImages] = useState<string[]>([]);
  const [dob, setDob] = useState('');
  const [gender, setGender] = useState('female');
  const [reason, setReason] = useState('');
  const action = useAction();
  const show = () =>
    action.run('show', async () => {
      const urls = [];
      for (let i = 0; i < item.documents; i++) {
        urls.push(await fileUrl(`/admin/identity/${item.id}/documents/${i}`));
      }
      setImages(urls);
    });
  const review = (approve: boolean) =>
    action.run('review', async () => {
      await api('POST', `/admin/identity/${item.id}/review`, approve ? { approve, date_of_birth: dob, gender } : { approve, reason });
      onDone();
    });
  return (
    <div className="card">
      <p><strong>{item.full_name}</strong> <span className="muted">{item.email} · {day(item.created_at)}</span></p>
      <button className="link" onClick={show}>{t('Open')} ({item.documents})</button>
      <div className="row">{images.map(u => <img key={u} src={u} alt="ID document" className="thumb" style={{ maxWidth: 320 }} />)}</div>
      <div className="row">
        <label>Date of birth<input type="date" value={dob} onChange={e => setDob(e.target.value)} /></label>
        <label>Gender<select value={gender} onChange={e => setGender(e.target.value)}><option value="female">female</option><option value="male">male</option></select></label>
        <button onClick={() => review(true)} disabled={!dob || action.busy !== null}>{t('Approve')}</button>
      </div>
      <div className="row">
        <label style={{ flex: 1 }}>Reason (if rejecting)<input value={reason} onChange={e => setReason(e.target.value)} /></label>
        <button className="danger" onClick={() => review(false)} disabled={action.busy !== null}>{t('Reject')}</button>
      </div>
      <ErrorNote error={action.error} />
    </div>
  );
}
