import { useEffect, useState } from 'react'
import { Activity, AlertTriangle, Database, Image, LoaderCircle, ScanSearch, Table2 } from 'lucide-react'
import { Link } from 'react-router-dom'
import { EmptyState, PageHeader, Panel } from '../components/Common.jsx'
import { useJob } from '../context/JobContext.jsx'
import { getAnalysis } from '../services/api.js'

function Stat({ icon: Icon, label, value, note }) {
  return <div className="card stat-card"><div className="stat-top">{label}<span className="stat-icon"><Icon size={16} /></span></div><div className="stat-value">{value}</div><div className="stat-caption">{note}</div></div>
}

export default function AnalysisPage() {
  const { job } = useJob()
  const [analysis, setAnalysis] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!job?.file_id) { setAnalysis(null); return }
    const controller = new AbortController()
    setLoading(true); setError('')
    getAnalysis(job.file_id, controller.signal).then(setAnalysis).catch((reason) => {
      if (!controller.signal.aborted) setError(reason.message)
    }).finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [job?.file_id])

  if (!job) return <><PageHeader eyebrow="ADDA · PROFILE" title="Data quality analysis" description="Review deterministic profiles and clearly labeled model predictions." /><Panel title="No uploaded file in this session"><EmptyState icon={ScanSearch} title="Upload a dataset first" description="The uploaded file ID is kept in this browser session only." action={<Link className="button primary" to="/upload">Upload a dataset</Link>} /></Panel></>

  const summary = analysis?.summary || {}
  const invalidCount = (summary.invalid_value_checks || []).reduce((total, check) => total + check.invalid_count, 0)
  return <>
    <PageHeader eyebrow="ADDA · PROFILE" title="Data quality analysis" description={`Backend profile for ${job.file_name}.`} action={<span className="badge blue">{job.data_type === 'tabular' ? 'CSV' : 'Image'} · {job.file_id.slice(0, 8)}</span>} />
    {loading && <div className="badge" role="status"><LoaderCircle size={13} className="spin" /> Loading backend analysis…</div>}
    {error && <div className="error-box" role="alert"><AlertTriangle size={15} />{error}</div>}
    {analysis?.data_type === 'tabular' && <>
      <div className="grid stats"><Stat icon={Database} label="Rows" value={summary.row_count ?? '—'} note="Backend CSV profile" /><Stat icon={Table2} label="Columns" value={summary.column_count ?? '—'} note="Original schema order" /><Stat icon={AlertTriangle} label="Missing values" value={summary.missing_value_count ?? '—'} note="Deterministic check" /><Stat icon={Activity} label="Duplicate rows" value={summary.duplicate_row_count ?? '—'} note="Deterministic check" /></div>
      <div className="grid two"><Panel title="Model predictions" subtitle="ADDA cell-level prediction is currently disabled"><div className="notice"><AlertTriangle size={16} style={{ flexShrink: 0 }} /><span>{analysis.message} Known estimator input size: {healthText(analysis.model_status, analysis.model_input_features)}. No predicted defects or confidence values are being shown.</span></div></Panel><Panel title="Numeric summary" subtitle="Pandas describe statistics; deterministic profile only">{Object.keys(summary.numeric_summary || {}).length ? <div className="table-wrap"><table className="table"><thead><tr><th>Column</th><th>Count</th><th>Mean</th><th>Min</th><th>Max</th></tr></thead><tbody>{Object.entries(summary.numeric_summary).map(([name, stats]) => <tr key={name}><td>{name}</td><td>{stats.count ?? '—'}</td><td>{formatNumber(stats.mean)}</td><td>{formatNumber(stats.min)}</td><td>{formatNumber(stats.max)}</td></tr>)}</tbody></table></div> : <EmptyState icon={Table2} title="No numeric columns" description="The uploaded CSV has no numeric fields to summarize." />}</Panel></div>
      <Panel title="Columns and deterministic checks" subtitle="Model predictions are not included in this table." className="section-gap"><div className="table-wrap"><table className="table"><thead><tr><th>Column</th><th>Data type</th><th>Missing</th><th>Missing %</th><th>Target</th></tr></thead><tbody>{(summary.columns || []).map((column) => <tr key={`${column.name}-${column.dtype}`}><td>{column.name}</td><td>{column.dtype}</td><td>{column.missing_count}</td><td>{column.missing_percent}%</td><td>{summary.protected_columns?.includes(column.name) ? <span className="badge">Protected</span> : '—'}</td></tr>)}</tbody></table></div><p className="stat-caption" style={{ marginTop: 10 }}>Mixed numeric checks: {invalidCount} candidate value(s) across {summary.invalid_value_checks?.length || 0} column(s). {summary.protected_columns?.length ? `Protected target: ${summary.protected_columns.join(', ')}.` : 'No diagnosis target column detected.'}</p></Panel>
    </>}
    {analysis?.data_type === 'image' && <Panel title="Image quality analysis" subtitle={`${job.file_name} · ${job.inspection?.format || 'Image'} · ${job.inspection?.width || '—'} × ${job.inspection?.height || '—'} px`}><EmptyState icon={Image} title="Image model preprocessing unavailable" description={analysis.message} /></Panel>}
    {analysis?.data_type === 'image_dataset' && <>
      <div className="grid stats">{[['Images', summary.image_count], ['Detected defects', summary.defect_total], ['Missing', summary.defect_counts?.missing], ['Corrupted', summary.defect_counts?.corrupted]].map(([name, value]) => <Stat key={name} icon={Image} label={name} value={value ?? '—'} note="Measured from the uploaded CSV and ZIP" />)}</div>
      <Panel title="Image quality checks" subtitle={summary.method}><div className="grid equal">{Object.entries(summary.defect_counts || {}).map(([name, value]) => <div className="workflow-step" key={name}><b>{value}</b><p>{name.replaceAll('_', ' ')}</p></div>)}</div></Panel>
      <Panel title="Image manifest records" subtitle="Real per-image file checks, dimensions and quality metrics" className="section-gap"><div className="table-wrap"><table className="table"><thead><tr><th>Image ID</th><th>Label</th><th>Image path</th><th>Status</th><th>Defects</th><th>Dimensions</th></tr></thead><tbody>{(summary.rows || []).map((row) => <tr key={row.image_id}><td>{row.image_id}</td><td>{row.class_label}</td><td>{row.image_path}</td><td>{row.status}</td><td>{row.defects.join(', ') || '—'}</td><td>{row.metrics ? `${row.metrics.width} × ${row.metrics.height}` : 'Unavailable'}</td></tr>)}</tbody></table></div></Panel>
    </>}
  </>
}

function formatNumber(value) { return value == null ? '—' : Number(value).toLocaleString(undefined, { maximumFractionDigits: 3 }) }
function healthText(status, featureCount) { return `${featureCount ?? 'unknown'}-feature model input; feature meanings are unverified (status: ${status})` }
