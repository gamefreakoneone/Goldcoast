import { useEffect, useState } from 'react'
import { api, authenticatedFetch } from './client'
import { PrivateImage } from './hooks'
import type { Asset, AssetRole, Business, Resource } from './types'

const roles: Record<AssetRole, string> = { product: 'Product photo', reference: 'Marketing material', logo: 'Logo', guidelines: 'PDF guidelines', font: 'Brand font', video: 'Context video', testimonial: 'Testimonial video' }
type Classification = { role: AssetRole; product_id: string | null; marketing_kind: 'owned' | 'inspiration'; source_url: string | null }
type Staged = Classification & { id: string; file: File; status: string; error: string }
const initial = (role: AssetRole): Classification => ({ role, product_id: null, marketing_kind: 'owned', source_url: null })

function FilePreview({ file }: { file: File }) {
  const [url, setUrl] = useState('')
  useEffect(() => { const value = URL.createObjectURL(file); setUrl(value); return () => URL.revokeObjectURL(value) }, [file])
  return file.type.startsWith('image/') && url ? <img src={url} alt={file.name}/> : <div className="document-tile">{file.type === 'video/mp4' ? 'Video' : 'Document'}</div>
}

function ClassificationFields({ value, products, change, disabled = false }: { value: Classification; products: Business['products']; change: (value: Classification) => void; disabled?: boolean }) {
  return <fieldset disabled={disabled} className="asset-classification"><label>Category<select value={value.role} onChange={e => change(initial(e.target.value as AssetRole))}>{Object.entries(roles).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label>
    {value.role === 'product' && <label>Product<select value={value.product_id ?? ''} onChange={e => change({ ...value, product_id: e.target.value || null })}><option value="">Unassigned - choose a product</option>{products.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}</select></label>}
    {value.role === 'reference' && <><label>Material belongs to<select value={value.marketing_kind} onChange={e => change({ ...value, marketing_kind: e.target.value as Classification['marketing_kind'] })}><option value="owned">Our past marketing</option><option value="inspiration">External inspiration</option></select></label>{value.marketing_kind === 'inspiration' && <label>Source URL<input type="url" required value={value.source_url ?? ''} onChange={e => change({ ...value, source_url: e.target.value || null })}/></label>}</>}
  </fieldset>
}

function AssetCard({ asset, products, onSaved, selected, onSelect }: { asset: Resource<Asset>; products: Business['products']; onSaved: () => Promise<void>; selected: boolean; onSelect: (checked: boolean) => void }) {
  const [value, setValue] = useState<Classification>({ ...initial(asset.data.role), product_id: asset.data.product_id ?? null, marketing_kind: asset.data.marketing_kind ?? 'owned', source_url: asset.data.source_url ?? null })
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const save = async () => { setBusy(true); setError(''); try { await api(`/assets/${asset.id}`, { version: asset.version, ...value }, 'PUT'); await onSaved() } catch (e) { setError(String(e)) } finally { setBusy(false) } }
  return <article className="asset-tile">
    {asset.data.mime.startsWith('image/') ? <PrivateImage path={`/assets/${asset.id}/content`} alt={asset.data.filename}/> : <div className="document-tile">{roles[asset.data.role]}</div>}
    <h3>{asset.data.filename}</h3><p className="small">{asset.data.role === 'reference' ? (asset.data.marketing_kind === 'inspiration' ? 'External inspiration' : 'Our past marketing') : roles[asset.data.role]}{asset.data.role === 'product' ? ` · ${products.find(p => p.id === asset.data.product_id)?.name ?? 'Unassigned'}` : ''}</p>
    {asset.data.source_url && <a href={asset.data.source_url} target="_blank" rel="noreferrer">Source attribution</a>}
    {asset.data.role === 'reference' && <label className="checkbox small"><input type="checkbox" checked={selected} onChange={e => onSelect(e.target.checked)}/>Use for visual style</label>}
    <details><summary>Edit classification</summary><ClassificationFields value={value} products={products} change={setValue} disabled={busy}/><button type="button" className="text-button" disabled={busy} onClick={() => void save()}>Save classification</button>{error && <p role="alert">{error}</p>}</details>
  </article>
}

export function AssetLibrary({ assets, business, onSaved, referenceIds, onReferences }: { assets: Resource<Asset>[]; business: Resource<Business> | null; onSaved: () => Promise<void>; referenceIds: string[]; onReferences: (ids: string[]) => void }) {
  const [queue, setQueue] = useState<Staged[]>([])
  const [category, setCategory] = useState<AssetRole>('product')
  const [rights, setRights] = useState(false)
  const [busy, setBusy] = useState(false)
  const products = business?.data.products ?? []
  const stage = (files: FileList | null) => { if (files) setQueue(old => [...old, ...Array.from(files).map(file => ({ ...initial(file.type === 'application/pdf' ? 'guidelines' : file.type === 'video/mp4' ? 'testimonial' : category), id: crypto.randomUUID(), file, status: 'Ready', error: '' }))]) }
  const update = (id: string, value: Partial<Staged>) => setQueue(old => old.map(item => item.id === id ? { ...item, ...value } : item))
  const upload = async () => {
    if (!rights || !business || busy) return
    setBusy(true)
    for (const item of queue.filter(q => q.status !== 'Uploaded')) {
      update(item.id, { status: 'Uploading', error: '' })
      try {
        const body = new FormData(); body.set('file', item.file); body.set('role', item.role); body.set('rights_confirmed', 'true'); body.set('marketing_kind', item.marketing_kind)
        if (item.product_id) body.set('product_id', item.product_id)
        if (item.source_url) body.set('source_url', item.source_url)
        await authenticatedFetch('/assets', { method: 'POST', body }); update(item.id, { status: 'Uploaded' })
      } catch (error) { update(item.id, { status: 'Failed', error: error instanceof Error ? error.message : String(error) }) }
    }
    try { await onSaved() } finally { setBusy(false) }
  }
  const groups: [string, AssetRole[]][] = [['Product photos', ['product']], ['Marketing material', ['reference']], ['Brand essentials', ['logo', 'guidelines', 'font', 'video']], ['Testimonials', ['testimonial']]]
  return <div className="asset-library">
    <label>New image category<select value={category} onChange={e => setCategory(e.target.value as AssetRole)}>{Object.entries(roles).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label>
    <div className="upload-zone" onDragOver={e => e.preventDefault()} onDrop={e => { e.preventDefault(); if (!busy) stage(e.dataTransfer.files) }}><h3>Drop your files here</h3><p>Review categories before uploading. Photos, PDFs, fonts and short videos.</p><label className="primary file-picker">Choose files<input type="file" multiple disabled={busy} accept="image/png,image/jpeg,image/webp,application/pdf,.woff,.woff2,.ttf,.otf,video/mp4" onChange={e => { stage(e.target.files); e.target.value = '' }}/></label></div>
    <p className="small muted">10 MB per file · 30 files per library · MP4 videos up to 60 seconds</p>
    {queue.length > 0 && <section><div className="section-header"><h3>Ready to organize ({queue.length})</h3><button type="button" className="text-button" disabled={busy} onClick={() => setQueue(old => old.map(q => q.status === 'Uploaded' ? q : { ...q, ...initial(category) }))}>Apply category to pending files</button></div><div className="asset-grid">{queue.map(item => <article className="asset-tile" key={item.id}><FilePreview file={item.file}/><h3>{item.file.name}</h3><ClassificationFields value={item} products={products} change={value => update(item.id, value)} disabled={busy || item.status === 'Uploaded'}/><p role="status">{item.status}</p>{item.error && <p role="alert">{item.error}</p>}<button type="button" className="text-button" disabled={busy} onClick={() => setQueue(old => old.filter(q => q.id !== item.id))}>Remove from queue</button></article>)}</div>
      <label className="checkbox"><input type="checkbox" checked={rights} onChange={e => setRights(e.target.checked)}/>I have permission to use this material.</label>
      {!business && <p><a href="#/business">Save your business details</a> before uploading. Your staged files stay here until you leave this page.</p>}
      {!rights && <p className="small muted">Confirm permission to enable upload.</p>}
      <button type="button" className="primary" disabled={busy || !business || !rights || queue.every(q => q.status === 'Uploaded')} onClick={() => void upload()}>{busy ? 'Uploading...' : 'Upload pending files / retry failures'}</button>
    </section>}
    {groups.map(([title, included]) => <section className="form-section" key={title}><h3>{title}</h3><div className="asset-grid">{assets.filter(a => included.includes(a.data.role)).map(asset => <AssetCard key={`${asset.id}-${asset.version}`} asset={asset} products={products} onSaved={onSaved} selected={referenceIds.includes(asset.id)} onSelect={checked => onReferences(checked ? [...referenceIds, asset.id] : referenceIds.filter(id => id !== asset.id))}/>)}</div>{!assets.some(a => included.includes(a.data.role)) && <p className="small muted">No {title.toLowerCase()} yet.</p>}</section>)}
  </div>
}
