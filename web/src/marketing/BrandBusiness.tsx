import { useState } from 'react'
import { api, authenticatedFetch } from './client'
import { PrivateImage, useRun } from './hooks'
import { Icon, Notice, PageHeading, Status } from './ui'
import type { Asset, AssetRole, Brand, Business, Resource, Run, Usage } from './types'

export const defaultBrand: Brand = {
  palette: ['#183D35', '#FFF9ED'], voice: 'Warm, clear and welcoming', typography: 'serif',
  layout: 'Product-led imagery with generous space', image_direction: 'Natural light and honest product photography',
  prohibited: [], reference_asset_ids: [], logo_asset_id: null, font_asset_id: null, uncertainty: [], confirmed: false,
}
const defaultBusiness: Business = {
  name: '', category: 'cafe', city: '', neighborhood: '', address: '', timezone: 'America/Los_Angeles',
  website: null, description: '', hours: '', products: [{ name: '', description: '', price: '' }], offers: [],
  audience: '', confirmed: false,
}
const message = (error: unknown) => error instanceof Error ? error.message : String(error)

export function BusinessPage({ value, onSaved }: { value: Resource<Business> | null; onSaved: () => Promise<void> }) {
  const [form, setForm] = useState<Business>(() => structuredClone(value?.data ?? defaultBusiness))
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [saved, setSaved] = useState(false)
  const change = <K extends keyof Business>(key: K, value: Business[K]) => setForm(previous => ({ ...previous, [key]: value }))
  const submit = async (event: React.FormEvent) => {
    event.preventDefault(); setBusy(true); setError(''); setSaved(false)
    try {
      await api('/business', { version: value?.version ?? 0, profile: { ...form,
        website: form.website?.trim() || null, products: form.products.filter(p => p.name.trim()) } }, 'PUT')
      await onSaved(); setSaved(true)
    } catch (reason) { setError(message(reason)) } finally { setBusy(false) }
  }
  return <><PageHeading title="A little about your business.">The facts your agents need to make something that fits.</PageHeading>
    {error && <Notice>{error}</Notice>}{saved && <Notice tone="success">Business details saved.</Notice>}
    <form className="panel business-form" onSubmit={submit}>
      <div className="form-grid"><label>Business name<input required maxLength={100} value={form.name} onChange={e => change('name', e.target.value)} /></label>
        <label>Business type<select value={form.category} onChange={e => change('category', e.target.value as Business['category'])}><option value="cafe">Café</option><option value="bakery">Bakery</option><option value="restaurant">Restaurant</option><option value="bar">Bar</option></select></label>
        <label>City<input required maxLength={100} value={form.city} onChange={e => change('city', e.target.value)} /></label>
        <label>Neighborhood<input maxLength={100} value={form.neighborhood} onChange={e => change('neighborhood', e.target.value)} /></label>
        <label>Address<input maxLength={250} value={form.address} onChange={e => change('address', e.target.value)} /></label>
        <label>Timezone<input list="timezones" value={form.timezone} onChange={e => change('timezone', e.target.value)} /><datalist id="timezones"><option>America/Los_Angeles</option><option>America/New_York</option><option>Europe/London</option><option>Asia/Kolkata</option></datalist></label>
        <label>Website<input type="url" value={form.website ?? ''} onChange={e => change('website', e.target.value)} placeholder="https://" /></label>
        <label>Opening hours<input maxLength={500} value={form.hours} onChange={e => change('hours', e.target.value)} placeholder="Mon–Sat, 7 am–5 pm" /></label>
      </div>
      <label>What makes your place special?<textarea maxLength={1500} value={form.description} onChange={e => change('description', e.target.value)} /></label>
      <label>Who would you like to reach?<input maxLength={500} value={form.audience} onChange={e => change('audience', e.target.value)} placeholder="Neighbors, commuters, weekend visitors…" /></label>
      <section className="form-section"><h2>What’s on the menu?</h2><p className="muted">Your agents can promote only the products you list here.</p>
        {form.products.map((product, index) => <div className="product-row" key={index}>
          <label>Product name<input aria-label={`Product ${index + 1} name`} maxLength={100} value={product.name} onChange={e => change('products', form.products.map((p, i) => i === index ? { ...p, name: e.target.value } : p))}/></label>
          <label>Description<input maxLength={500} value={product.description} onChange={e => change('products', form.products.map((p, i) => i === index ? { ...p, description: e.target.value } : p))}/></label>
          <label>Price (optional)<input maxLength={40} value={product.price} onChange={e => change('products', form.products.map((p, i) => i === index ? { ...p, price: e.target.value } : p))}/></label>
          <button type="button" className="icon-button" aria-label={`Remove product ${index + 1}`} onClick={() => change('products', form.products.filter((_, i) => i !== index))}><Icon name="close"/></button>
        </div>)}
        <button type="button" className="text-button" disabled={form.products.length >= 40} onClick={() => change('products', [...form.products, { name: '', price: '', description: '' }])}><Icon name="plus" size={18}/>Add a product</button>
      </section>
      <section className="form-section"><h2>Current offers <span className="optional">Optional</span></h2><p className="muted">No discount or offer will be invented on your behalf.</p>
        {form.offers.map((offer, index) => <div className="offer-row" key={index}><label>Exact offer<input required maxLength={200} value={offer.text} onChange={e => change('offers', form.offers.map((o, i) => i === index ? { ...o, text: e.target.value } : o))}/></label>
          <label>Valid through<input required type="date" value={offer.valid_until} onChange={e => change('offers', form.offers.map((o, i) => i === index ? { ...o, valid_until: e.target.value } : o))}/></label>
          <button type="button" className="icon-button" aria-label="Remove offer" onClick={() => change('offers', form.offers.filter((_, i) => i !== index))}><Icon name="close"/></button></div>)}
        <button type="button" className="text-button" disabled={form.offers.length >= 5} onClick={() => change('offers', [...form.offers, { text: '', valid_until: '', confirmed: true }])}><Icon name="plus" size={18}/>Add an offer</button>
      </section>
      <label className="checkbox"><input type="checkbox" checked={form.confirmed} onChange={e => change('confirmed', e.target.checked)}/>I confirm these business details, products, and offers.</label>
      <div className="form-footer"><button className="primary" disabled={busy}>{busy ? 'Saving…' : 'Save business details'}</button><span className="muted">Changes make previous campaigns out of date.</span></div>
    </form></>
}

export function BrandPage({ brand, assets, business, usage, analysisId, onAnalysis, onSaved }: {
  brand: Resource<Brand> | null; assets: Resource<Asset>[]; business: Resource<Business> | null;
  usage: Usage; analysisId: string | null; onAnalysis: (id: string) => void; onSaved: () => Promise<void>;
}) {
  const [kit, setKit] = useState<Brand>(() => structuredClone(brand?.data ?? defaultBrand))
  const [avoidText, setAvoidText] = useState((brand?.data.prohibited ?? []).join(', '))
  const [role, setRole] = useState<AssetRole>('reference')
  const [rights, setRights] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const analysis = useRun(analysisId)
  const change = <K extends keyof Brand>(key: K, value: Brand[K]) => setKit(previous => ({ ...previous, [key]: value, confirmed: key === 'confirmed' ? Boolean(value) : false }))
  const upload = async (files: FileList | null) => {
    if (!files?.length) return
    if (!rights) { setError('Confirm you have permission to use this material first.'); return }
    setBusy(true); setError(''); setNotice('')
    try {
      for (const file of Array.from(files)) {
        const body = new FormData(); body.set('file', file); body.set('role', role); body.set('rights_confirmed', 'true')
        await authenticatedFetch('/assets', { method: 'POST', body })
      }
      await onSaved(); setNotice('Your material is in the brand library.')
    } catch (reason) { setError(message(reason)) } finally { setBusy(false) }
  }
  const analyze = async () => {
    setBusy(true); setError('')
    try { const run = await api<Run>('/brand/analyze', {}); onAnalysis(run.id); await onSaved() }
    catch (reason) { setError(message(reason)) } finally { setBusy(false) }
  }
  const save = async (event: React.FormEvent) => {
    event.preventDefault(); setBusy(true); setError('')
    try { await api('/brand', { version: brand?.version ?? 0, kit }, 'PUT'); await onSaved(); setNotice('Brand kit saved.') }
    catch (reason) { setError(message(reason)) } finally { setBusy(false) }
  }
  const draft = analysis.result && 'palette' in analysis.result ? analysis.result : null
  return <><PageHeading title="Your brand, without the prompt.">Bring your photos, past ads, and guidelines. We’ll learn the style.</PageHeading>
    {error && <Notice>{error}</Notice>}{notice && <Notice tone="success">{notice}</Notice>}
    {!business && <Notice tone="info">Save your business details before uploading material.</Notice>}
    {analysis.run && <Notice tone={analysis.run.state === 'failed' ? 'error' : 'info'}>Brand analysis: {analysis.run.state}.{draft && <button className="text-button" onClick={() => { setKit({ ...draft, confirmed: false }); setAvoidText(draft.prohibited.join(', ')); setNotice('Review the draft below, then confirm and save it.') }}>Review the new draft<Icon name="arrow" size={16}/></button>}{analysis.run.state === 'failed' && ' No automatic retry was made. Check the workflow activity or contact the owner.'}</Notice>}
    <div className="brand-grid"><section className="panel"><h2>Your marketing material</h2>
      <div className="upload-zone" onDragOver={e => e.preventDefault()} onDrop={e => { e.preventDefault(); void upload(e.dataTransfer.files) }}>
        <Icon name="upload" size={34}/><h3>Drop your files here</h3><p>Photos, logos, past ads, PDF guidelines, fonts, or a short video</p>
        <label className={`primary file-picker ${busy || !business ? 'disabled' : ''}`}>Choose files<input type="file" multiple disabled={busy || !business} accept="image/png,image/jpeg,image/webp,application/pdf,.woff,.woff2,.ttf,.otf,video/mp4" onChange={e => { void upload(e.target.files); e.target.value = '' }}/></label>
      </div>
      <div className="upload-options"><label>Use these files as<select value={role} onChange={e => setRole(e.target.value as AssetRole)}><option value="reference">Reference images or past ads</option><option value="product">Product photos</option><option value="logo">Logo</option><option value="guidelines">PDF guidelines</option><option value="font">Brand font</option><option value="video">Short video</option></select></label><p className="small muted">10 MB per file · 30 files per library<br/>Videos: MP4, up to 60 seconds</p></div>
      <label className="checkbox"><input type="checkbox" checked={rights} onChange={e => setRights(e.target.checked)}/>I have permission to use this material.</label>
      <div className="asset-grid">{assets.map(asset => <article className="asset-tile" key={asset.id}>
        {asset.data.mime.startsWith('image/') ? <PrivateImage path={`/assets/${asset.id}/content`} alt={asset.data.filename}/> : <div className="document-tile"><Icon name={asset.data.role === 'video' ? 'campaigns' : 'brand'} size={36}/><span>{asset.data.role}</span></div>}
        <h3 title={asset.data.filename}>{asset.data.filename}</h3><span className="small muted">{asset.data.role === 'product' ? 'Product photo' : asset.data.role}</span>
        {asset.data.mime.startsWith('image/') && <label className="checkbox small"><input type="checkbox" checked={kit.reference_asset_ids.includes(asset.id)} onChange={e => change('reference_asset_ids', e.target.checked ? [...kit.reference_asset_ids, asset.id] : kit.reference_asset_ids.filter(id => id !== asset.id))}/>Use as reference</label>}
      </article>)}</div>
      {!assets.length && <p className="empty-note">Start with a photo you love or an ad that feels like you.</p>}
      <div className="form-footer"><button className="primary" onClick={() => void analyze()} disabled={busy || !assets.some(a => a.data.mime.startsWith('image/')) || !usage.live_enabled || usage.brand_remaining < 1 || Boolean(usage.active_job)}>Analyze my brand</button><span className="small muted">Uses 1 brand analysis<br/>{usage.brand_remaining} remaining</span></div>
      {!usage.live_enabled && <p className="small muted">Live analysis is paused. You can still set your brand direction below.</p>}
    </section><form className="panel kit-panel" onSubmit={save}><div className="section-header"><h2>Your visual direction</h2><Status good={kit.confirmed}>{kit.confirmed ? 'Confirmed' : 'Draft · review needed'}</Status></div>
      <label>Color palette</label><div className="palette">{kit.palette.map((color, index) => <label key={index}><input type="color" aria-label={`Brand color ${index + 1}`} value={color} onChange={e => change('palette', kit.palette.map((c, i) => i === index ? e.target.value : c))}/><span>{color.toUpperCase()}</span></label>)}{kit.palette.length < 6 && <button type="button" className="icon-button" aria-label="Add brand color" onClick={() => change('palette', [...kit.palette, '#C76F3D'])}><Icon name="plus"/></button>}</div>
      <label>Voice<input maxLength={500} value={kit.voice} onChange={e => change('voice', e.target.value)}/></label>
      <label>Typography<select value={kit.typography} onChange={e => change('typography', e.target.value as Brand['typography'])}><option value="serif">Serif</option><option value="sans">Sans serif</option><option value="mono">Monospace</option></select></label>
      <label>Image direction<textarea maxLength={800} value={kit.image_direction} onChange={e => change('image_direction', e.target.value)}/></label>
      <label>Avoid<input value={avoidText} onChange={e => { setAvoidText(e.target.value); change('prohibited', e.target.value.split(',').map(v => v.trim()).filter(Boolean)) }} placeholder="Separate words or phrases with commas"/></label>
      <details><summary>Layout, logo, and font</summary><label>Layout<input maxLength={500} value={kit.layout} onChange={e => change('layout', e.target.value)}/></label>
        <label>Original logo<select value={kit.logo_asset_id ?? ''} onChange={e => change('logo_asset_id', e.target.value || null)}><option value="">Use business name</option>{assets.filter(a => a.data.role === 'logo').map(a => <option key={a.id} value={a.id}>{a.data.filename}</option>)}</select></label>
        <label>Uploaded font<select value={kit.font_asset_id ?? ''} onChange={e => change('font_asset_id', e.target.value || null)}><option value="">Use selected typography</option>{assets.filter(a => a.data.role === 'font').map(a => <option key={a.id} value={a.id}>{a.data.filename}</option>)}</select></label></details>
      {kit.uncertainty.length > 0 && <div className="small muted"><strong>Worth checking</strong><ul>{kit.uncertainty.map((note, i) => <li key={i}>{note}</li>)}</ul></div>}
      <label className="checkbox"><input type="checkbox" checked={kit.confirmed} onChange={e => change('confirmed', e.target.checked)}/>I’ve reviewed this brand direction.</label>
      <button className="primary full" disabled={busy || !business}>{busy ? 'Working…' : 'Save brand kit'}</button>
    </form></div></>
}
