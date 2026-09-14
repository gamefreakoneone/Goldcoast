import { useEffect, useState } from 'react'
import { api, authenticatedFetch } from './client'
import { PrivateImage } from './hooks'
import type { Asset, AssetRole, Business, Resource } from './types'

const roles: Record<AssetRole, string> = { product: 'Product photo', reference: 'Marketing material', logo: 'Logo', guidelines: 'PDF guidelines', font: 'Brand font', video: 'Campaign video', testimonial: 'Legacy testimonial' }
const visibleRoles: AssetRole[] = ['product', 'reference', 'logo', 'guidelines', 'font', 'video']
type Classification = { role: AssetRole; product_id: string | null; marketing_kind: 'owned' | 'inspiration'; source_url: string | null; title: string; description: string }
type Staged = Classification & { id: string; file: File; status: string; error: string }
const initial = (role: AssetRole): Classification => ({ role, product_id: null, marketing_kind: 'owned', source_url: null, title: '', description: '' })

function FilePreview({ file }: { file: File }) {
  const [url, setUrl] = useState('')
  useEffect(() => { const value = URL.createObjectURL(file); setUrl(value); return () => URL.revokeObjectURL(value) }, [file])
  return file.type.startsWith('image/') && url ? <img src={url} alt={file.name}/> : file.type === 'video/mp4' && url ? <video className="campaign-video-preview" controls muted src={url} aria-label={file.name}/> : <div className="document-tile">Document</div>
}

function PrivateVideo({ asset }: { asset: Resource<Asset> }) {
  const [url, setUrl] = useState('')
  useEffect(() => {
    let live = true
    let objectUrl = ''
    authenticatedFetch(`/assets/${asset.id}/content`).then(async response => {
      if (!response.ok) throw new Error('Video unavailable')
      objectUrl = URL.createObjectURL(await response.blob())
      if (live) setUrl(objectUrl)
    }).catch(() => undefined)
    return () => { live = false; if (objectUrl) URL.revokeObjectURL(objectUrl) }
  }, [asset.id])
  return url ? <video className="campaign-video-preview" controls muted src={url} aria-label={asset.data.title || asset.data.filename}/> : <div className="document-tile">Campaign video</div>
}

function ClassificationFields({ value, products, change, disabled = false }: { value: Classification; products: Business['products']; change: (value: Classification) => void; disabled?: boolean }) {
  return <fieldset disabled={disabled} className="asset-classification"><label>Category<select value={value.role} onChange={e => change(initial(e.target.value as AssetRole))}>{visibleRoles.map(key => <option key={key} value={key}>{roles[key]}</option>)}</select></label>
    {(value.role === 'product' || value.role === 'video') && <label>Product <span className="optional">Optional</span><select value={value.product_id ?? ''} onChange={e => change({ ...value, product_id: e.target.value || null })}><option value="">No product selected</option>{products.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}</select></label>}
    {value.role === 'video' && <><label>Video name<input required maxLength={100} value={value.title} onChange={e => change({ ...value, title: e.target.value })} placeholder="Limited Edition Boba Tea"/></label><label>What does this video show?<textarea required maxLength={500} value={value.description} onChange={e => change({ ...value, description: e.target.value })} placeholder="A close-up pour and finished cup available today."/></label><p className="small muted">Products and limited-time offers must also be confirmed on the Business page.</p></>}
    {value.role === 'reference' && <><label>Material belongs to<select value={value.marketing_kind} onChange={e => change({ ...value, marketing_kind: e.target.value as Classification['marketing_kind'] })}><option value="owned">Our past marketing</option><option value="inspiration">External inspiration</option></select></label>{value.marketing_kind === 'inspiration' && <label>Source URL<input type="url" required value={value.source_url ?? ''} onChange={e => change({ ...value, source_url: e.target.value || null })}/></label>}</>}
  </fieldset>
}

function AssetCard({ asset, products, onSaved, selected, onSelect }: { asset: Resource<Asset>; products: Business['products']; onSaved: () => Promise<void>; selected: boolean; onSelect: (checked: boolean) => void }) {
  const [value, setValue] = useState<Classification>({ ...initial(asset.data.role), product_id: asset.data.product_id ?? null, marketing_kind: asset.data.marketing_kind ?? 'owned', source_url: asset.data.source_url ?? null, title: asset.data.title ?? '', description: asset.data.description ?? '' })
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const save = async () => { setBusy(true); setError(''); try { await api(`/assets/${asset.id}`, { version: asset.version, ...value }, 'PUT'); await onSaved() } catch (e) { setError(String(e)) } finally { setBusy(false) } }
  return <article className="asset-tile">
    {asset.data.mime.startsWith('image/') ? <PrivateImage path={`/assets/${asset.id}/content`} alt={asset.data.filename}/> : asset.data.role === 'video' ? <PrivateVideo asset={asset}/> : <div className="document-tile">{roles[asset.data.role]}</div>}
    <h3>{asset.data.role === 'video' ? asset.data.title || asset.data.filename : asset.data.filename}</h3><p className="small">{asset.data.role === 'reference' ? (asset.data.marketing_kind === 'inspiration' ? 'External inspiration' : 'Our past marketing') : roles[asset.data.role]}{['product', 'video'].includes(asset.data.role) ? ` · ${products.find(p => p.id === asset.data.product_id)?.name ?? 'No product selected'}` : ''}</p>
    {asset.data.role === 'video' && <p className="video-description">{asset.data.description || 'Add a description before using this video in a new campaign.'}</p>}
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
  const stage = (files: FileList | null) => { if (files) setQueue(old => [...old, ...Array.from(files).map(file => ({ ...initial(file.type === 'application/pdf' ? 'guidelines' : file.type === 'video/mp4' ? 'video' : category), id: crypto.randomUUID(), file, status: 'Ready', error: '' }))]) }
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
        if (item.title) body.set('title', item.title)
        if (item.description) body.set('description', item.description)
        await authenticatedFetch('/assets', { method: 'POST', body }); update(item.id, { status: 'Uploaded' })
      } catch (error) { update(item.id, { status: 'Failed', error: error instanceof Error ? error.message : String(error) }) }
    }
    try { await onSaved() } finally { setBusy(false) }
  }
  const groups: [string, AssetRole[]][] = [['Campaign videos', ['video']], ['Product photos', ['product']], ['Marketing material', ['reference']], ['Brand essentials', ['logo', 'guidelines', 'font']]]
  const incompleteVideo = queue.some(item => item.status !== 'Uploaded' && item.role === 'video' && (!item.title.trim() || !item.description.trim()))
  return <div className="asset-library">
    <label>New file category<select value={category} onChange={e => setCategory(e.target.value as AssetRole)}>{visibleRoles.map(key => <option key={key} value={key}>{roles[key]}</option>)}</select></label>
    <div className="upload-zone" onDragOver={e => e.preventDefault()} onDrop={e => { e.preventDefault(); if (!busy) stage(e.dataTransfer.files) }}><h3>Drop your files here</h3><p>Review categories before uploading. Photos, PDFs, fonts and short videos.</p><label className="primary file-picker">Choose files<input type="file" multiple disabled={busy} accept="image/png,image/jpeg,image/webp,application/pdf,.woff,.woff2,.ttf,.otf,video/mp4" onChange={e => { stage(e.target.files); e.target.value = '' }}/></label></div>
    <p className="small muted">10 MB per file · 30 files per library · MP4 videos up to 60 seconds</p>
    {queue.length > 0 && <section><div className="section-header"><h3>Ready to organize ({queue.length})</h3><button type="button" className="text-button" disabled={busy} onClick={() => setQueue(old => old.map(q => q.status === 'Uploaded' ? q : { ...q, ...initial(category) }))}>Apply category to pending files</button></div><div className="asset-grid">{queue.map(item => <article className="asset-tile" key={item.id}><FilePreview file={item.file}/><h3>{item.file.name}</h3><ClassificationFields value={item} products={products} change={value => update(item.id, value)} disabled={busy || item.status === 'Uploaded'}/><p role="status">{item.status}</p>{item.error && <p role="alert">{item.error}</p>}<button type="button" className="text-button" disabled={busy} onClick={() => setQueue(old => old.filter(q => q.id !== item.id))}>Remove from queue</button></article>)}</div>
      <label className="checkbox"><input type="checkbox" checked={rights} onChange={e => setRights(e.target.checked)}/>I have permission to use this material.</label>
      {!business && <p><a href="#/business">Save your business details</a> before uploading. Your staged files stay here until you leave this page.</p>}
      {!rights && <p className="small muted">Confirm permission to enable upload.</p>}
      {incompleteVideo && <p className="small muted">Name and describe every campaign video before uploading.</p>}
      <button type="button" className="primary" disabled={busy || !business || !rights || incompleteVideo || queue.every(q => q.status === 'Uploaded')} onClick={() => void upload()}>{busy ? 'Uploading...' : 'Upload pending files / retry failures'}</button>
    </section>}
    {groups.map(([title, included]) => <section className="form-section" key={title}><h3>{title}</h3><div className="asset-grid">{assets.filter(a => included.includes(a.data.role)).map(asset => <AssetCard key={`${asset.id}-${asset.version}`} asset={asset} products={products} onSaved={onSaved} selected={referenceIds.includes(asset.id)} onSelect={checked => onReferences(checked ? [...referenceIds, asset.id] : referenceIds.filter(id => id !== asset.id))}/>)}</div>{!assets.some(a => included.includes(a.data.role)) && <p className="small muted">No {title.toLowerCase()} yet.</p>}</section>)}
  </div>
}
