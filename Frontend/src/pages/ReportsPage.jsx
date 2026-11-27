import { useCallback, useEffect, useState } from 'react'
import { AlertTriangle, CheckCircle2, Download, FileJson2, FileSpreadsheet, FileText, Image, LoaderCircle, RefreshCw } from 'lucide-react'
import { Link } from 'react-router-dom'
import { EmptyState, PageHeader, Panel } from '../components/Common.jsx'
import { useJob } from '../context/JobContext.jsx'
import { downloadArtifact, getReport } from '../services/api.js'
import { artifactIsDownloadable, reportPageStatus } from './reportsUtils.js'

const artifactTypes = [
  ['cleaned_csv', FileSpreadsheet, 'Cleaned CSV', (id) => `autoclean_${id}_cleaned.csv`],
  ['repair_history_csv', FileText, 'Repair history CSV', (id) => `autoclean_${id}_repair_history.csv`],
  ['quality_report', FileJson2, 'Quality report JSON', (id) => `autoclean_${id}_quality_report.json`],
  ['validation_report', FileJson2, 'Validation report JSON', (id) => `autoclean_${id}_validation_report.json`],
  ['repaired_image', Image, 'Repaired image dataset ZIP', (id) => `autoclean_${id}_repaired_images.zip`],
]

export default function ReportsPage() {
  const { job } = useJob()
  const [report, setReport] = useState(null)
  const [reportFileId, setReportFileId] = useState('')
  const [loading, setLoading] = useState(false)
  const [downloading, setDownloading] = useState('')
  const [error, setError] = useState('')

  const refresh = useCallback(async (signal) => {
    if (!job?.file_id) { setReport(null); setReportFileId(''); setLoading(false); setError(''); return }
    setLoading(true)
    setError('')
    setReport(null)
    setReportFileId('')
    try {
      setReport(await getReport(job.file_id, signal))
      setReportFileId(job.file_id)
    } catch (reason) {
      if (!signal?.aborted) setError(reason.message)
    } finally {
      if (!signal?.aborted) setLoading(false)
    }
  }, [job?.file_id])

  useEffect(() => {
    const controller = new AbortController()
    refresh(controller.signal)
    return () => controller.abort()
  }, [refresh])

  const handleDownload = async (key, artifact, filename) => {
    if (!artifact?.download_url) return
    setDownloading(key)
    setError('')
    try {
      await downloadArtifact(artifact.download_url, filename(job.file_id))
    } catch (reason) {
      setError(reason.message)
    } finally {
      setDownloading('')
    }
  }

  const activeReport = reportFileId === job?.file_id ? report : null
  const statusLabel = reportPageStatus(job, loading, activeReport)

  return <>
    <PageHeader eyebrow="OUTPUTS" title="Reports & downloads" description="Download only artifacts generated for the active uploaded file." action={<div style={{ display: 'flex', alignItems: 'center', gap: 8 }}><span className="badge" role="status">{statusLabel}</span><button className="button" onClick={() => refresh()} disabled={!job || loading} title="Refresh report and artifact availability"><RefreshCw size={13} />Refresh</button></div>} />
    {!job
      ? <Panel title="No active upload"><EmptyState icon={FileText} title="Upload a file first" description="Reports and downloads are tied to the uploaded file ID in this browser session." action={<Link className="button primary" to="/upload">Go to upload</Link>} /></Panel>
      : <>
        <div className="notice" style={{ marginBottom: 17 }}><CheckCircle2 size={16} style={{ flexShrink: 0 }} /><span><b>{job.file_name}</b> · {job.data_type === 'tabular' ? 'CSV dataset' : job.data_type === 'image_dataset' ? 'Image CSV + ZIP dataset' : 'Image file'} · File ID <code>{job.file_id}</code>. Availability is checked against stored backend artifacts.</span></div>
        {loading && <span className="badge" role="status"><LoaderCircle size={13} className="spin" /> Generating quality report and checking outputs…</span>}
        {error && <div className="error-box" role="alert"><AlertTriangle size={14} />{error}<button className="button" onClick={() => refresh()} disabled={loading}>Retry</button></div>}
        {activeReport && <div className="helper-note section-gap" role="status">Job status: <b>{activeReport.status}</b>. {activeReport.message}</div>}
        <Panel title="Available artifacts" subtitle={activeReport ? `Backend status: ${activeReport.status}` : 'Checking the backend'} className="section-gap">
          <div className="step-list">{artifactTypes.map(([key, Icon, title, filename]) => {
            const artifact = activeReport?.[key]
            const available = artifactIsDownloadable(artifact)
            const isDownloading = downloading === key
            return <div className="step-row" key={key}><span className="step-count"><Icon size={14} /></span><div style={{ flex: 1, minWidth: 0 }}><b>{title}</b><p>{artifact?.message || (loading ? 'Checking availability…' : 'No report response yet.')}</p></div><span className="badge">{available ? 'Generated' : 'Not generated'}</span><button className="button" onClick={() => handleDownload(key, artifact, filename)} disabled={!available || Boolean(downloading)} aria-disabled={!available || Boolean(downloading)} title={available ? `Download ${title}` : artifact?.message || 'This artifact has not been generated'}>{isDownloading ? <LoaderCircle size={13} className="spin" /> : <Download size={13} />}{isDownloading ? 'Preparing…' : 'Download'}</button></div>
          })}</div>
        </Panel>
        <Panel title="Report contents" subtitle="Generated from the current upload and real backend results" className="section-gap"><p className="stat-caption">The quality report contains the source filename, data type, analysis timestamp, and available profile values such as columns, missing counts, duplicate rows and numeric summaries. The validation report is available only after ARVA has saved actual checks for this file. Image quality metrics and image repair are not implemented.</p></Panel>
      </>}
  </>
}
