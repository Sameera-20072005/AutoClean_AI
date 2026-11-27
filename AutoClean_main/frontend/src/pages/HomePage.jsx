import { useEffect, useState } from 'react'
import { ArrowRight, Circle, Image, ScanSearch, ShieldCheck, Sparkles, Table2 } from 'lucide-react'
import { Link } from 'react-router-dom'
import { PageHeader, Panel, PrimaryLink } from '../components/Common.jsx'
import { getBackendHealth } from '../services/api.js'
import './HomePage.css'

function readiness(model, checking) {
  if (checking) return 'Initializing'
  return model?.prediction_ready === true ? 'Ready' : 'Unavailable'
}

export default function HomePage() {
  const [health, setHealth] = useState('checking')
  useEffect(() => {
    const controller = new AbortController()
    getBackendHealth(controller.signal).then(setHealth).catch(() => {
      if (!controller.signal.aborted) setHealth('unavailable')
    })
    return () => controller.abort()
  }, [])

  const checking = health === 'checking'
  const connected = typeof health === 'object' && health !== null && health.status === 'ok'
  const services = [
    ['Backend', checking ? 'Initializing' : connected ? 'Ready' : 'Unavailable'],
    ['Tabular AI', readiness(connected ? health.models?.tabular : null, checking)],
    ['Image AI', readiness(connected ? health.models?.image : null, checking)],
  ]

  return <>
    <section className="hero-panel"><div className="hero-panel-content"><div className="eyebrow">SMART MULTIMODAL DATA CLEANING</div><h1>Make your data<br />ready to trust.</h1><p>Inspect quality issues, review repair suggestions and validate each change with a transparent workflow built for tabular data and images.</p><PrimaryLink to="/upload">Start cleaning</PrimaryLink></div></section>
    <PageHeader title="A clearer path to quality data" description="Three stages keep detection, repair and validation transparent from start to finish." />
    <div className="feature-grid">{[[ScanSearch, '01', 'ADDA · Detect', 'Adaptive Data Defect Detection identifies supported data quality issues. Model predictions and deterministic checks are clearly separated.'], [Sparkles, '02', 'ADRA · Repair', 'Review proposed changes before accepting them. Original data stays preserved and each approved change can be audited.'], [ShieldCheck, '03', 'ARVA · Validate', 'Check remaining issues, schema preservation and repair history, with warnings and limitations included.']].map(([Icon, num, title, desc]) => <article className="card feature-card" key={num}><span className="feature-number">{num}</span><div className="stat-icon"><Icon size={17} /></div><h3>{title}</h3><p>{desc}</p></article>)}</div>
    <div className="grid two section-gap"><Panel title="Designed for two data types" subtitle="Upload experiences support both formats."><div className="grid equal"><div className="workflow-step"><Table2 size={17} color="#536ee5" /><b>Tabular datasets</b><p>CSV profiling is available. Model predictions require the notebook feature builder and a safe reference strategy.</p></div><div className="workflow-step"><Image size={17} color="#8c68cc" /><b>Image files</b><p>Image validation is available. Classification requires a verified feature extractor and class-name mapping.</p></div></div></Panel>
      <Panel title="Service status" subtitle="Live availability of AutoClean AI services."><div className="home-service-status" role="status">{services.map(([name, state]) => <div className="home-service-row" key={name}><span className="home-service-name">{name}</span><span className={`home-service-value ${state.toLowerCase()}`}><Circle size={9} fill="currentColor" strokeWidth={0} />{state}</span></div>)}</div>{services.slice(1).some(([, state]) => state === 'Unavailable') && <p className="home-service-note">This feature is temporarily unavailable.</p>}<Link to="/about" className="button" style={{ marginTop: 14 }}>Project details <ArrowRight size={13} /></Link></Panel></div>
    <Panel title="From upload to validation" subtitle="Each step has a dedicated place in the workspace." className="section-gap"><div className="workflow">{[['1', 'Upload', 'Choose a CSV or image.'], ['2', 'Analyze', 'Inspect data profiles and model findings.'], ['3', 'Review repair', 'Approve supported changes.'], ['4', 'Validate', 'Check outcomes and reports.']].map(([num, title, desc]) => <div className="workflow-step" key={num}><span className="step-count">{num}</span><b>{title}</b><p>{desc}</p></div>)}</div></Panel>
  </>
}
