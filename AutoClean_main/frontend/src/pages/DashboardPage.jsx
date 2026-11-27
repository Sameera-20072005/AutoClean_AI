import { useEffect, useState } from 'react'
import { Activity, AlertTriangle, CheckCircle2, Database, FileStack, LoaderCircle, RefreshCw, Wrench } from 'lucide-react'
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { EmptyState, PageHeader, Panel, Tooltip as Tip } from '../components/Common.jsx'
import { getDashboard } from '../services/api.js'

export default function DashboardPage() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const refresh = async (signal) => {
    setLoading(true)
    setError('')
    try { setData(await getDashboard(signal)) }
    catch (reason) { if (!signal?.aborted) setError(reason.message) }
    finally { if (!signal?.aborted) setLoading(false) }
  }

  useEffect(() => {
    const controller = new AbortController()
    refresh(controller.signal)
    return () => controller.abort()
  }, [])

  const stats = data ? [
    [Database, 'Datasets processed', data.datasets_processed, 'Stored uploads', ''],
    [FileStack, 'Files analyzed', data.files_analyzed, 'Files with available profiles', 'violet'],
    [Activity, 'Defects detected', data.defects_detected, 'From current stored datasets', 'orange'],
    [CheckCircle2, 'Repairs completed', data.repairs_completed, `${data.records_repaired} records or cells changed`, 'green'],
  ] : []

  return <>
    <PageHeader eyebrow="OVERVIEW" title="Dashboard" description="A live summary of stored uploads, analysis, repairs and validation." action={<button className="button" onClick={() => refresh()} disabled={loading}><RefreshCw size={13} />Refresh</button>} />
    {loading && <span className="badge" role="status"><LoaderCircle size={13} className="spin" /> Loading backend activity…</span>}
    {error && <div className="error-box" role="alert"><AlertTriangle size={15} />{error}</div>}
    {data && <>
      <div className="grid stats">{stats.map(([Icon, title, value, caption, color]) => <article className="card stat-card" key={title}><div className="stat-top"><span>{title} <Tip text="Calculated from uploaded files and actual backend artifacts." /></span><span className={`stat-icon ${color}`}><Icon size={16} /></span></div><div className="stat-value">{value}</div><div className="stat-caption">{caption}</div></article>)}</div>
      <div className="grid two">
        <Panel title="Upload activity" subtitle="Uploads by recorded UTC date">
          {data.activity.length ? <div className="chart-wrap" role="img" aria-label="Uploads by date"><ResponsiveContainer width="100%" height="100%"><AreaChart data={data.activity} margin={{ top: 10, right: 5, left: -24, bottom: 0 }}><defs><linearGradient id="activityFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#667be8" stopOpacity={.2} /><stop offset="95%" stopColor="#667be8" stopOpacity={0} /></linearGradient></defs><CartesianGrid stroke="#eff1f6" strokeDasharray="3 4" vertical={false} /><XAxis dataKey="day" tickFormatter={(day) => day.slice(5)} tickLine={false} axisLine={false} tick={{ fontSize: 10, fill: '#929bad' }} /><YAxis allowDecimals={false} tickLine={false} axisLine={false} tick={{ fontSize: 10, fill: '#929bad' }} /><Tooltip /><Area dataKey="uploads" name="Uploads" stroke="#667be8" strokeWidth={2} fill="url(#activityFill)" /></AreaChart></ResponsiveContainer></div> : <EmptyState icon={Activity} title="No upload activity" description="Uploaded datasets will appear here." />}
        </Panel>
        <Panel title="Validation results" subtitle="Saved ARVA results from repair jobs"><div className="grid equal"><div className="workflow-step"><b>{data.validation.passed}</b><p>Passed</p></div><div className="workflow-step"><b>{data.validation.failed}</b><p>Failed</p></div><div className="workflow-step"><b>{data.validation.not_run}</b><p>Not run</p></div></div>{data.warnings.length > 0 && <div className="step-list section-gap">{data.warnings.slice(0, 5).map((warning) => <div className="step-row" key={`${warning.file_id}-${warning.message}`}><span className="step-count"><AlertTriangle size={13} /></span><div><b>{warning.file_name}</b><p>{warning.message}</p></div></div>)}</div>}{!data.warnings.length && <p className="stat-caption section-gap">No defects or failed validations were found in the stored uploads.</p>}</Panel>
      </div>
      <Panel title="Recent datasets" subtitle="Uploaded files and their actual backend processing state" className="section-gap">{data.jobs.length ? <div className="table-wrap"><table className="table"><thead><tr><th>Dataset</th><th>Type</th><th>Uploaded</th><th>Defects</th><th>Repaired</th><th>Validation</th></tr></thead><tbody>{data.jobs.map((job) => <tr key={job.file_id}><td><b>{job.file_name}</b><br /><span className="stat-caption">{job.summary}</span></td><td>{job.data_type}</td><td>{job.uploaded_at ? new Date(job.uploaded_at).toLocaleString() : '—'}</td><td>{job.defects_detected}</td><td>{job.records_repaired}</td><td><span className="badge">{job.validation_status.replaceAll('_', ' ')}</span></td></tr>)}</tbody></table></div> : <EmptyState icon={Database} title="No uploaded datasets" description="Upload and analyze a CSV or image to populate this dashboard." />}</Panel>
      <Panel title="Repair history" subtitle="Rows read from generated repair history artifacts" className="section-gap">{data.repair_history.length ? <div className="table-wrap"><table className="table"><thead><tr><th>Dataset</th><th>Row</th><th>Column</th><th>Method</th><th>Old value</th><th>New value</th></tr></thead><tbody>{data.repair_history.map((entry, index) => <tr key={`${entry.file_id}-${entry.row_index}-${entry.column}-${index}`}><td>{entry.file_name}</td><td>{entry.row_index}</td><td>{entry.column}</td><td>{entry.method?.replaceAll('_', ' ')}</td><td>{entry.old_value || '∅'}</td><td>{entry.new_value}</td></tr>)}</tbody></table></div> : <EmptyState icon={Wrench} title="No repairs recorded" description="Actual changes will be listed here after a supported repair completes." />}</Panel>
    </>}
  </>
}
