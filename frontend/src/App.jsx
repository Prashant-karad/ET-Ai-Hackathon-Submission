import { useEffect, useState } from 'react'
import { api } from './api'

const EMPTY_KNOWLEDGE = {
  expert_name: '', role_experience: '', equipment: '', common_problem: '', first_check: '',
  root_cause: '', fix_workaround: '', junior_mistake: '', warning_sign: '',
}

const STEPS = [
  { key: 'expert_name', title: 'Who is sharing this knowledge?', hint: 'Use the name colleagues would recognize.', placeholder: 'e.g. Maya Patel', type: 'input' },
  { key: 'role_experience', title: 'What is their role and experience?', hint: 'A short role and years in the field is enough.', placeholder: 'e.g. Senior Mechanical Technician, 18 years', type: 'input' },
  { key: 'equipment', title: 'Which equipment or asset is this about?', hint: 'Include the asset tag if it is known.', placeholder: 'e.g. Raw Water Intake Pump P-101', type: 'input' },
  { key: 'common_problem', title: 'What problem do you see most often?', hint: 'Describe the situation an operator would notice.', placeholder: 'e.g. Low-flow alarms during hot weather despite normal motor speed.', type: 'area' },
  { key: 'first_check', title: 'What is the first thing you check?', hint: 'Record the initial diagnostic check, not the full fix.', placeholder: 'e.g. Suction pressure and strainer differential pressure.', type: 'area' },
  { key: 'root_cause', title: 'What usually causes it?', hint: 'Share the pattern that experience has taught you to recognise.', placeholder: 'e.g. A loaded strainer or air entering at the suction gasket.', type: 'area' },
  { key: 'fix_workaround', title: 'How do you fix it or work around it?', hint: 'Keep it practical and in the order you would normally act.', placeholder: 'e.g. Clean the strainer, replace the gasket, prime, and restart slowly.', type: 'area' },
  { key: 'junior_mistake', title: 'What mistake do juniors commonly make?', hint: 'This is often the part that prevents repeat incidents.', placeholder: 'e.g. Raising pump speed before checking suction conditions.', type: 'area' },
  { key: 'warning_sign', title: 'Is there an early warning sign?', hint: 'Optional — leave blank if there is no reliable sign.', placeholder: 'e.g. Crackling at the casing with fluctuating discharge pressure.', type: 'area', optional: true },
]

function Notice({ message, tone = 'neutral' }) {
  const colours = tone === 'error' ? 'border-red-200 bg-red-50 text-red-800' : tone === 'success' ? 'border-emerald-200 bg-emerald-50 text-emerald-800' : 'border-slate-200 bg-slate-50 text-slate-700'
  return <div className={`rounded-lg border px-3.5 py-3 text-sm ${colours}`}>{message}</div>
}

function Stats({ stats }) {
  const entries = [
    ['Documents ingested', stats.documents],
    ['Expert cards captured', stats.cards],
    ['Questions asked', stats.questions],
  ]
  return <div className="grid gap-2 sm:grid-cols-3">{entries.map(([label, value]) => <div className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-2.5" key={label}><p className="text-[11px] font-medium uppercase tracking-[0.1em] text-slate-400">{label}</p><p className="mt-0.5 text-xl font-semibold text-white">{value}</p></div>)}</div>
}

function CaptureWizard({ refreshStats }) {
  const [values, setValues] = useState(() => {
    try { return { ...EMPTY_KNOWLEDGE, ...JSON.parse(localStorage.getItem('plant-knowledge-draft') || '{}') } } catch { return EMPTY_KNOWLEDGE }
  })
  const [step, setStep] = useState(0)
  const [stage, setStage] = useState('capture')
  const [card, setCard] = useState('')
  const [mode, setMode] = useState('')
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState(null)
  const current = STEPS[step]

  useEffect(() => { localStorage.setItem('plant-knowledge-draft', JSON.stringify(values)) }, [values])
  const update = (key, value) => setValues((previous) => ({ ...previous, [key]: value }))
  const validCurrent = current.optional || values[current.key].trim().length >= 2

  async function next() {
    if (!validCurrent) { setNotice({ message: 'Please add a short answer before continuing.', tone: 'error' }); return }
    setNotice(null)
    if (step < STEPS.length - 1) { setStep(step + 1); return }
    setBusy(true)
    try {
      const result = await api.generateCard(values)
      setCard(result.card_text)
      setMode(result.mode)
      setStage('review')
    } catch (error) { setNotice({ message: error.message, tone: 'error' }) } finally { setBusy(false) }
  }

  async function save() {
    if (card.trim().length < 20) { setNotice({ message: 'The knowledge card needs a little more detail before it can be saved.', tone: 'error' }); return }
    setBusy(true)
    try {
      const result = await api.saveCard({ ...values, card_text: card })
      setNotice({ message: result.message, tone: 'success' })
      refreshStats()
      localStorage.removeItem('plant-knowledge-draft')
    } catch (error) { setNotice({ message: error.message, tone: 'error' }) } finally { setBusy(false) }
  }

  if (stage === 'review') return <section className="panel overflow-hidden"><div className="border-b border-slate-200 bg-mist px-5 py-5 sm:px-7"><div className="flex flex-wrap items-center justify-between gap-3"><div><p className="text-xs font-semibold uppercase tracking-[0.14em] text-amber">Review before saving</p><h2 className="mt-1 text-2xl font-semibold tracking-tight text-ink">Knowledge card</h2><p className="mt-1 text-sm text-slate-600">{values.equipment} · {values.expert_name}</p></div>{mode === 'local' && <span className="rounded-full border border-amber/30 bg-amber/10 px-3 py-1 text-xs font-semibold text-amber">Local formatting mode</span>}</div></div><div className="space-y-4 px-5 py-6 sm:px-7"><p className="text-sm leading-6 text-slate-600">Edit the wording if needed. Saving creates one searchable expert knowledge card for the whole plant team.</p><textarea className="field min-h-80 font-mono text-sm" value={card} onChange={(event) => setCard(event.target.value)} aria-label="Editable knowledge card" />{notice && <Notice {...notice} />}<div className="flex flex-col-reverse gap-3 border-t border-slate-100 pt-5 sm:flex-row sm:justify-between"><button className="quiet-button" onClick={() => { setStage('capture'); setNotice(null) }} disabled={busy}>Back to answers</button><button className="primary-button" onClick={save} disabled={busy}>{busy ? 'Saving…' : 'Confirm & save card'}</button></div></div></section>

  return <section className="panel overflow-hidden"><div className="border-b border-slate-200 bg-mist px-5 py-5 sm:px-7"><div className="flex flex-wrap items-end justify-between gap-3"><div><p className="text-xs font-semibold uppercase tracking-[0.14em] text-amber">Expert knowledge capture</p><h2 className="mt-1 text-2xl font-semibold tracking-tight text-ink">Capture what experience knows</h2></div><p className="text-sm font-medium text-slate-600">Step {step + 1} of {STEPS.length}</p></div><div className="mt-4 h-1.5 overflow-hidden rounded-full bg-slate-200"><div className="h-full rounded-full bg-amber transition-all" style={{ width: `${((step + 1) / STEPS.length) * 100}%` }} /></div></div><div className="px-5 py-7 sm:px-7"><div className="mx-auto max-w-2xl"><p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">{current.optional ? 'Optional detail' : 'Required detail'}</p><h3 className="mt-2 text-2xl font-semibold leading-tight tracking-tight text-ink">{current.title}</h3><p className="mt-2 text-sm leading-6 text-slate-600">{current.hint}</p><div className="mt-7">{current.type === 'input' ? <input autoFocus className="field" value={values[current.key]} placeholder={current.placeholder} onChange={(event) => update(current.key, event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter') next() }} /> : <textarea autoFocus className="field min-h-36 resize-y" value={values[current.key]} placeholder={current.placeholder} onChange={(event) => update(current.key, event.target.value)} />}</div>{notice && <div className="mt-4"><Notice {...notice} /></div>}<div className="mt-8 flex items-center justify-between border-t border-slate-100 pt-5"><button className="quiet-button" onClick={() => { setStep(Math.max(0, step - 1)); setNotice(null) }} disabled={step === 0 || busy}>Back</button><button className="primary-button" onClick={next} disabled={busy}>{busy ? 'Preparing card…' : step === STEPS.length - 1 ? 'Create knowledge card' : 'Continue'}</button></div></div></div></section>
}

function Documents({ refreshStats }) {
  const [documents, setDocuments] = useState([])
  const [file, setFile] = useState(null)
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState(null)
  const load = async () => { try { setDocuments(await api.documents()) } catch (error) { setNotice({ message: error.message, tone: 'error' }) } }
  useEffect(() => { load() }, [])
  async function submit(event) { event.preventDefault(); if (!file) { setNotice({ message: 'Choose a file to add to the knowledge base.', tone: 'error' }); return }; setBusy(true); setNotice(null); try { const result = await api.upload(file); setNotice({ message: `${result.source_name} was indexed into ${result.chunk_count} searchable chunk${result.chunk_count === 1 ? '' : 's'}.`, tone: 'success' }); setFile(null); event.target.reset(); await load(); refreshStats() } catch (error) { setNotice({ message: error.message, tone: 'error' }) } finally { setBusy(false) } }
  return <section className="grid gap-5 lg:grid-cols-[0.9fr_1.1fr]"><div className="panel p-5 sm:p-7"><p className="text-xs font-semibold uppercase tracking-[0.14em] text-amber">Ingest documents</p><h2 className="mt-1 text-2xl font-semibold tracking-tight">Add a trusted source</h2><p className="mt-3 text-sm leading-6 text-slate-600">Upload manuals, procedures, logs, or shift records. Each file is split into searchable passages and kept alongside expert knowledge.</p><form className="mt-6 space-y-4" onSubmit={submit}><label className="block rounded-lg border border-dashed border-slate-300 bg-slate-50 p-5 text-center hover:border-amber"><span className="block text-sm font-semibold text-ink">{file ? file.name : 'Choose a .txt, .csv, or .pdf file'}</span><span className="mt-1 block text-xs text-slate-500">Maximum size: 10 MB</span><input className="sr-only" type="file" accept=".txt,.csv,.pdf" onChange={(event) => setFile(event.target.files?.[0] || null)} /></label><button className="primary-button w-full" disabled={busy}>{busy ? 'Indexing document…' : 'Add to knowledge base'}</button></form>{notice && <div className="mt-4"><Notice {...notice} /></div>}</div><div className="panel overflow-hidden"><div className="border-b border-slate-200 px-5 py-5 sm:px-6"><h2 className="font-semibold text-ink">Ingested documents</h2><p className="mt-1 text-sm text-slate-500">Stored locally and available to every search.</p></div><div className="divide-y divide-slate-100">{documents.length ? documents.map((doc) => <div className="flex gap-3 px-5 py-4 sm:px-6" key={doc.id}><span className="mt-0.5 text-lg">📄</span><div className="min-w-0 flex-1"><p className="truncate text-sm font-semibold text-ink">{doc.source_name}</p><p className="mt-1 text-xs text-slate-500">{doc.chunk_count} chunk{doc.chunk_count === 1 ? '' : 's'} · {doc.equipment_tag} · {new Date(doc.uploaded_at).toLocaleDateString()}</p></div></div>) : <div className="px-5 py-14 text-center text-sm text-slate-500">No documents yet. The bundled demo data is a good place to start.</div>}</div></div></section>
}

function Ask({ openCapture, refreshStats }) {
  const [question, setQuestion] = useState('')
  const [result, setResult] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  async function submit(event) { event.preventDefault(); if (question.trim().length < 2) return; setBusy(true); setError(''); try { setResult(await api.ask(question)); refreshStats() } catch (err) { setError(err.message) } finally { setBusy(false) } }
  return <section className="mx-auto max-w-4xl"><div className="panel p-5 sm:p-7"><p className="text-xs font-semibold uppercase tracking-[0.14em] text-amber">Unified knowledge search</p><h2 className="mt-1 text-2xl font-semibold tracking-tight">Ask the plant knowledge base</h2><p className="mt-2 text-sm leading-6 text-slate-600">Results combine indexed documents and confirmed field knowledge. Every answer shows its source material.</p><form className="mt-6 flex flex-col gap-3 sm:flex-row" onSubmit={submit}><input className="field flex-1" value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="e.g. What should I check first for a P-101 low-flow alarm?" /><button className="primary-button shrink-0" disabled={busy}>{busy ? 'Searching…' : 'Ask question'}</button></form>{error && <div className="mt-4"><Notice message={error} tone="error" /></div>}</div>{result && <div className="mt-5 space-y-4"><div className="panel p-5 sm:p-7"><div className="flex flex-wrap items-center justify-between gap-3"><h3 className="font-semibold text-ink">Answer</h3><span className={`rounded-full px-3 py-1 text-xs font-semibold ${result.mode === 'local' ? 'bg-amber/10 text-amber' : 'bg-emerald-50 text-emerald-700'}`}>{result.mode === 'local' ? 'Local retrieval mode' : 'Groq synthesis'}</span></div><p className="mt-4 whitespace-pre-wrap text-[15px] leading-7 text-slate-700">{result.answer}</p></div>{result.no_strong_match && <div className="rounded-xl border border-amber/30 bg-amber/10 p-5 sm:flex sm:items-center sm:justify-between sm:gap-6"><div><p className="font-semibold text-ink">No strong match found in the knowledge base.</p><p className="mt-1 text-sm text-slate-700">Would you like to capture this as new expert knowledge?</p></div><button className="quiet-button mt-4 shrink-0 border-amber/40 bg-white sm:mt-0" onClick={openCapture}>Capture knowledge</button></div>}<div className="panel overflow-hidden"><div className="border-b border-slate-200 px-5 py-4 sm:px-6"><h3 className="font-semibold text-ink">Sources used</h3></div><div className="divide-y divide-slate-100">{result.sources.length ? result.sources.map((source) => <div className="flex items-center gap-3 px-5 py-4 sm:px-6" key={source.citation}><span className="text-lg">{source.doc_type === 'expert_knowledge' ? '🧠' : '📄'}</span><div className="min-w-0 flex-1"><p className="text-sm font-semibold text-ink">[{source.citation}] {source.source_name}</p><p className="mt-0.5 text-xs text-slate-500">{source.doc_type === 'expert_knowledge' ? 'Expert knowledge' : 'Document'} · {source.equipment_tag}</p></div><span className="text-xs font-medium text-slate-500">{Math.round(source.score * 100)}% match</span></div>) : <div className="px-5 py-8 text-sm text-slate-500">No source passages were available.</div>}</div></div></div>}</section>
}

export default function App() {
  const [tab, setTab] = useState('capture')
  const [stats, setStats] = useState({ documents: 0, cards: 0, questions: 0 })
  const [seedMessage, setSeedMessage] = useState('')
  const [seeding, setSeeding] = useState(false)
  const refreshStats = async () => { try { setStats(await api.dashboard()) } catch { /* backend may still be starting */ } }
  useEffect(() => { refreshStats() }, [])
  async function seed() { setSeeding(true); setSeedMessage(''); try { const result = await api.seed(); setSeedMessage(`${result.message} ${result.documents_added} document(s) and ${result.cards_added} card(s) added.`); refreshStats() } catch (error) { setSeedMessage(error.message) } finally { setSeeding(false) } }
  const tabs = [['documents', 'Ingest Documents'], ['capture', 'Capture Expert Knowledge'], ['ask', 'Ask']]
  return <div className="min-h-screen"><header className="border-b border-slate-700 bg-ink"><div className="mx-auto max-w-6xl px-4 py-5 sm:px-6"><div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between"><div><div className="flex items-center gap-2"><span className="inline-flex h-7 w-7 items-center justify-center rounded bg-amber text-sm font-bold text-white">P</span><p className="text-sm font-semibold tracking-wide text-white">Plant Knowledge Desk</p></div><p className="mt-1 text-sm text-slate-400">Industrial knowledge intelligence platform</p></div><div className="w-full lg:w-[500px]"><Stats stats={stats} /></div></div></div></header><main className="mx-auto max-w-6xl px-4 py-7 sm:px-6"><div className="mb-6 flex flex-col gap-3 border-b border-slate-300 sm:flex-row sm:items-center sm:justify-between"><nav className="flex gap-1 overflow-x-auto" aria-label="Primary navigation">{tabs.map(([id, label]) => <button key={id} onClick={() => setTab(id)} className={`whitespace-nowrap border-b-2 px-3 py-3 text-sm font-semibold ${tab === id ? 'border-amber text-ink' : 'border-transparent text-slate-500 hover:text-ink'}`}>{label}</button>)}</nav><button className="quiet-button mb-2 shrink-0 py-2 text-xs" onClick={seed} disabled={seeding}>{seeding ? 'Loading demo…' : 'Load demo data'}</button></div>{seedMessage && <div className="mb-5"><Notice message={seedMessage} tone={seedMessage.startsWith('Demo data') ? 'success' : 'error'} /></div>}{tab === 'capture' && <CaptureWizard refreshStats={refreshStats} />}{tab === 'documents' && <Documents refreshStats={refreshStats} />}{tab === 'ask' && <Ask openCapture={() => setTab('capture')} refreshStats={refreshStats} />}</main></div>
}
