import { useEffect, useState, type FormEvent } from 'react';

import { api, day, fileUrl } from '../api';
import { useI18n } from '../i18n';
import { ErrorNote, Loading, Page, useAction, useData } from '../ui';

type Item = { id: string; kind: string; title: Record<string, string>; category: string | null; tags: Record<string, string[]>;
  licence: string; content_status: string; is_active: boolean; created_at: string };

/**
 * Garments and hairstyles for try-on (rows 11, 12). Upload a front-facing
 * photo of a model wearing the garment (whole body, arms not over it) or a
 * frontal portrait with the hairstyle. The cut-out is made automatically;
 * check it and approve it before customers see it. Only use photos the client
 * has the rights to.
 */
export function TryOnLibrary() {
  const { t } = useI18n();
  const list = useData(() => api<Item[]>('GET', '/admin/tryon-items'));
  const [kind, setKind] = useState('garment');
  const [titleEn, setTitleEn] = useState('');
  const [titleAr, setTitleAr] = useState('');
  const [licence, setLicence] = useState('');
  const [category, setCategory] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const action = useAction();

  const upload = (e: FormEvent) => {
    e.preventDefault();
    if (!file) {
      return;
    }
    action.run('upload', async () => {
      const form = new FormData();
      form.append('file', file);
      form.append('kind', kind);
      form.append('title_en', titleEn);
      form.append('title_ar', titleAr);
      form.append('licence', licence);
      if (category) {
        form.append('category', category);
      }
      await api('POST', '/admin/tryon-items', form);
      setTitleEn('');
      setTitleAr('');
      setFile(null);
      await list.reload();
    }, 'Cut out. Check it below and approve it.');
  };

  return (
    <Page title="Try-on library" intro="Garments: front-facing, full body, arms away from the garment. Hairstyles: frontal portrait, hair visible. Not generative: the piece keeps the drape of the reference photo.">
      <form className="card" onSubmit={upload}>
        <div className="row">
          <label>Kind<select value={kind} onChange={e => setKind(e.target.value)} data-testid="tryon-kind"><option value="garment">garment</option><option value="hairstyle">hairstyle</option></select></label>
          <label>Category<input value={category} onChange={e => setCategory(e.target.value)} placeholder={kind === 'garment' ? 'dress, top, abaya…' : 'short, medium, long…'} /></label>
        </div>
        <div className="row">
          <label style={{ flex: 1 }}>Title (English)<input value={titleEn} onChange={e => setTitleEn(e.target.value)} required data-testid="tryon-title-en" /></label>
          <label style={{ flex: 1 }}>Title (Arabic)<input value={titleAr} onChange={e => setTitleAr(e.target.value)} required dir="rtl" data-testid="tryon-title-ar" /></label>
        </div>
        <label>Photo rights<input value={licence} onChange={e => setLicence(e.target.value)} required minLength={3} placeholder="e.g. Brand X lookbook, licensed until 2027" data-testid="tryon-licence" /></label>
        <label>Reference photo (JPEG or PNG)<input type="file" accept="image/jpeg,image/png" onChange={e => setFile(e.target.files?.[0] ?? null)} data-testid="tryon-file" /></label>
        <button type="submit" disabled={!file || action.busy !== null} data-testid="tryon-upload">{t('Create')}</button>
        {action.done ? <p className="ok">{action.done}</p> : null}
        <ErrorNote error={action.error} />
      </form>
      <ErrorNote error={list.error} />
      <Loading loading={list.loading} empty={list.data?.length === 0} />
      <div className="row" style={{ alignItems: 'stretch' }}>
        {list.data?.map(i => <ItemCard key={i.id} item={i} onChange={list.reload} />)}
      </div>
    </Page>
  );
}

function ItemCard({ item, onChange }: { item: Item; onChange: () => void }) {
  const { t } = useI18n();
  const [image, setImage] = useState<string | null>(null);
  const [tags, setTags] = useState(Object.entries(item.tags).map(([k, v]) => `${k}: ${v.join(', ')}`).join('; '));
  const action = useAction();
  useEffect(() => {
    fileUrl(`/admin/tryon-items/${item.id}/image`).then(setImage).catch(() => undefined);
  }, [item.id]);
  const patch = (body: Record<string, unknown>) =>
    action.run('patch', async () => {
      await api('PATCH', `/admin/tryon-items/${item.id}`, body);
      onChange();
    });
  const parsed = () => Object.fromEntries(tags.split(';').map(p => p.split(':')).filter(p => p.length === 2 && p[0].trim())
    .map(([k, v]) => [k.trim(), v.split(',').map(x => x.trim()).filter(Boolean)]));
  return (
    <div className="card" style={{ width: 260 }} data-testid={`tryon-${item.title.en}`}>
      {image ? <img src={image} alt={item.title.en} className="thumb" /> : null}
      <p><strong>{item.title.en}</strong> <span className="muted">{item.kind}{item.category ? ` · ${item.category}` : ''}</span></p>
      <p className="muted">{item.licence} · {day(item.created_at)}</p>
      <p>{item.content_status === 'approved' ? <span className="pill on">approved</span> : <span className="pill">draft</span>}</p>
      <label>Suits<input value={tags} onChange={e => setTags(e.target.value)} placeholder="face_shape: oval, round" dir="ltr" /></label>
      <div className="row">
        <button className="link" onClick={() => patch({ tags: parsed() })}>{t('Save')}</button>
        {item.content_status === 'approved' ? (
          <button className="link" onClick={() => patch({ content_status: 'draft' })}>Withdraw</button>
        ) : (
          <button onClick={() => patch({ content_status: 'approved', tags: parsed() })} data-testid={`approve-${item.title.en}`}>{t('Approve')}</button>
        )}
        <button className="link" onClick={() => window.confirm('Delete this item and its photo?') && action.run('delete', async () => { await api('DELETE', `/admin/tryon-items/${item.id}`); onChange(); })}>{t('Delete')}</button>
      </div>
      <ErrorNote error={action.error} />
    </div>
  );
}
