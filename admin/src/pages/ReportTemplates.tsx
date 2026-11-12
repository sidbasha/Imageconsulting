import { useState } from 'react';

import { api } from '../api';
import { useI18n } from '../i18n';
import { Bilingual, ErrorNote, Loading, Page, useAction, useData } from '../ui';

type Section = { key: string; title: Record<string, string>; type: string; options: string[]; required: boolean };
type Template = { key: string; service_kind: string; title: Record<string, string>; sections: Section[]; is_active: boolean; content_status: string };
const TYPES = ['decision', 'choice', 'text', 'list', 'palette'];

/** Standard expert report templates (rows 25, 56). Changes apply to reports written afterwards and to how earlier ones display. */
export function ReportTemplates() {
  const list = useData(() => api<Template[]>('GET', '/admin/report-templates'));
  return (
    <Page title="Report templates" intro="Every template keeps the standard frame: suitability, explanation, recommendations.">
      <ErrorNote error={list.error} />
      <Loading loading={list.loading} />
      {list.data?.map(tpl => <TemplateEditor key={tpl.key} template={tpl} onSaved={list.reload} />)}
    </Page>
  );
}

function TemplateEditor({ template, onSaved }: { template: Template; onSaved: () => void }) {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState(template.title);
  const [sections, setSections] = useState<Section[]>(template.sections.map(s => ({ ...s, options: s.options ?? [], required: s.required ?? false })));
  const [approved, setApproved] = useState(template.content_status === 'approved');
  const action = useAction();
  const update = (i: number, changes: Partial<Section>) => setSections(list => list.map((s, j) => (j === i ? { ...s, ...changes } : s)));
  const move = (i: number, by: number) =>
    setSections(list => {
      const next = [...list];
      const [item] = next.splice(i, 1);
      next.splice(Math.max(0, Math.min(next.length, i + by)), 0, item);
      return next;
    });
  const save = () =>
    action.run('save', async () => {
      await api('PUT', `/admin/report-templates/${template.key}`, { title, sections, is_active: template.is_active, content_status: approved ? 'approved' : 'draft' });
      onSaved();
    }, t('Saved'));
  return (
    <div className="card">
      <div className="row">
        <strong>{template.title.en}</strong><span className="muted">{template.service_kind} · {template.content_status}</span>
        <button className="link" onClick={() => setOpen(!open)} data-testid={`edit-${template.key}`}>{open ? t('Cancel') : 'Edit'}</button>
      </div>
      {open ? (
        <>
          <Bilingual label="Title" value={title} onChange={setTitle} />
          {sections.map((s, i) => (
            <div key={i} className="card">
              <div className="row">
                <label>Key<input value={s.key} onChange={e => update(i, { key: e.target.value })} dir="ltr" /></label>
                <label>Type<select value={s.type} onChange={e => update(i, { type: e.target.value })}>{TYPES.map(x => <option key={x}>{x}</option>)}</select></label>
                <label style={{ flexDirection: 'row' }}><input type="checkbox" checked={s.required} onChange={e => update(i, { required: e.target.checked })} /> Required</label>
                <button className="link" onClick={() => move(i, -1)}>↑</button>
                <button className="link" onClick={() => move(i, 1)}>↓</button>
                <button className="link" onClick={() => setSections(list => list.filter((_, j) => j !== i))}>{t('Delete')}</button>
              </div>
              <Bilingual label="Heading" value={s.title} onChange={v => update(i, { title: v })} />
              {['decision', 'choice'].includes(s.type) ? (
                <label>Options (comma-separated keys)<input value={s.options.join(', ')} dir="ltr"
                  onChange={e => update(i, { options: e.target.value.split(',').map(x => x.trim()).filter(Boolean) })} /></label>
              ) : null}
            </div>
          ))}
          <div className="row">
            <button className="link" onClick={() => setSections([...sections, { key: 'new_section', title: { en: '', ar: '' }, type: 'text', options: [], required: false }])}>+ Section</button>
            <label style={{ flexDirection: 'row' }}><input type="checkbox" checked={approved} onChange={e => setApproved(e.target.checked)} /> Approved by the client</label>
            <button onClick={save} disabled={action.busy !== null}>{t('Save')}</button>
            {action.done ? <span className="ok">{action.done}</span> : null}
          </div>
          <ErrorNote error={action.error} />
        </>
      ) : null}
    </div>
  );
}
