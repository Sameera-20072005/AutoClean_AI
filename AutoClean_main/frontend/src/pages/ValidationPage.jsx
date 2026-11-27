import { useEffect, useState } from 'react'
import { AlertTriangle, CheckCircle2, CircleX, FileCheck2, GitCompareArrows, LoaderCircle, ShieldCheck } from 'lucide-react'
import { Link } from 'react-router-dom'
import { EmptyState, PageHeader, Panel } from '../components/Common.jsx'
import { useJob } from '../context/JobContext.jsx'
import { getValidation } from '../services/api.js'

const label = (value) => value.replaceAll('_', ' ')

export default function ValidationPage() {
  const { job } = useJob()
  const [report, setReport] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!job?.file_id) { setReport(null); return }
    const controller = new AbortController()
    setLoading(true); setError('')
    getValidation(job.file_id, controller.signal).then(setReport).catch((reason) => {
      if (!controller.signal.aborted) setError(reason.message)
    }).finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [job?.file_id])

  const checks = report?.checks || []
  const passed = checks.filter((check) => check.passed).length
  const failed = checks.filter((check) => !check.passed).length
  const schemaPassed = checks.find((check) => check.name === 'columns_preserved')?.passed

  return <>
    <PageHeader eyebrow="ARVA · VALIDATE" title="Repair validation" description="ARVA checks the generated CSV and preservation of the original data." action={<span className="badge">{report?.status || 'No validation run'}</span>} />
    <div className="grid stats">{[[CheckCircle2, 'Passed checks', report ? passed : '—', report ? 'Actual ARVA results' : 'No validation results'], [AlertTriangle, 'Warnings', report?.status === 'not_available' ? '—' : 0, report ? 'No warning checks defined' : 'Not evaluated'], [CircleX, 'Failed checks', report ? failed : '—', report ? 'Actual ARVA results' : 'No validation results'], [FileCheck2, 'Schema preserved', schemaPassed === undefined ? '—' : schemaPassed ? 'Yes' : 'No', schemaPassed === undefined ? 'Not evaluated' : 'Actual ARVA result']].map(([Icon, title, value, caption]) => <div className="card stat-card" key={title}><div className="stat-top">{title}<span className="stat-icon"><Icon size={16} /></span></div><div className="stat-value">{value}</div><div className="stat-caption">{caption}</div></div>)}</div>
    {loading && <span className="badge" role="status"><LoaderCircle size={13} className="spin" /> Checking validation status…</span>}
    {error && <div className="error-box" role="alert">{error}</div>}
    <div className="grid two"><Panel title="Validation status" subtitle={report?.status === 'passed' ? 'Generated repair output checked' : 'Awaiting an actual repair output'}>{report && report.status !== 'not_available' ? <div className="notice"><ShieldCheck size={16} /><span><b>ARVA {report.status}.</b> {report.message}</span></div> : <EmptyState icon={ShieldCheck} title={report?.status === 'not_available' ? 'No repair validation yet' : 'Waiting for a repair output'} description={report?.message || 'Upload a CSV and run a supported repair before ARVA can validate it.'} />}</Panel><Panel title="Checks performed" subtitle="Only checks returned by the backend are listed">{checks.length ? <div className="step-list">{checks.map((check) => <div className="step-row" key={check.name}><span className="step-count">{check.passed ? <CheckCircle2 size={13} /> : <CircleX size={13} />}</span><div style={{ flex: 1 }}><b>{label(check.name)}</b><p>{check.passed ? 'Passed' : 'Failed'}</p></div><span className="badge">{check.passed ? 'Passed' : 'Failed'}</span></div>)}</div> : <EmptyState icon={GitCompareArrows} title="No checks recorded" description="Checks appear after an actual repair output has been validated." />}</Panel></div>
    <Panel title="Validation report" subtitle={job ? `File: ${job.file_name}` : 'No uploaded file in this session'} className="section-gap">{!job && <EmptyState icon={GitCompareArrows} title="Upload a file first" description="Validation results are linked to the uploaded file ID." action={<Link className="button" to="/upload">Start with a file</Link>} />}{job && <p className="stat-caption">{report?.message || 'No validation report has been returned for this file.'}</p>}</Panel>
  </>
}
