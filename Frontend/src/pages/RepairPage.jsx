import { useState } from 'react'
import { ArrowDownToLine, Check, Info, LoaderCircle, Wrench } from 'lucide-react'
import { Link } from 'react-router-dom'
import { EmptyState, PageHeader, Panel } from '../components/Common.jsx'
import { useJob } from '../context/JobContext.jsx'
import { getOutputUrl, requestRepair } from '../services/api.js'

export default function RepairPage() {
  const { job } = useJob()
  const [checking, setChecking] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')

  const runRepair = async () => {
    if (!job) return
    setChecking(true)
    setError('')
    setResult(null)
    try {
      setResult(await requestRepair(job.file_id))
    } catch (reason) {
      setError(reason.message)
    } finally {
      setChecking(false)
    }
  }

  return <>
    <PageHeader eyebrow="ADRA · REVIEW" title="Repair review" description={job?.data_type === 'image_dataset' ? 'Supported image repairs are saved in an output ZIP; unresolved images are marked for manual review.' : 'Supported missing values are repaired in an output copy; the uploaded source is preserved.'} />
    <div className="grid two">
      <Panel title="Supported repair methods" subtitle={job?.data_type === 'image_dataset' ? 'Deterministic image operations; trained ADRA remains unverified' : 'Conservative deterministic imputation'}>
        {job?.data_type === 'image_dataset' ? <div className="step-list">
          {[
            ['Noise', 'OpenCV colored denoising runs when measured noise exceeds the configured threshold.'],
            ['Blur', 'An unsharp mask is used for low-Laplacian images; lost detail cannot be recovered.'],
            ['Low resolution and missing files', 'Cubic scaling raises the short edge to 64 px. Files are matched by image ID in the archive; unresolved rows require manual review.'],
          ].map(([title, desc], index) => <div className="step-row" key={title}><span className="step-count">{index + 1}</span><div><b>{title}</b><p>{desc}</p></div></div>)}
        </div> : <div className="step-list">
          {[
            ['Numeric feature values', 'Missing values are filled with that column’s median.'],
            ['Categorical feature values', 'Missing values are filled with the most frequent observed value.'],
            ['Protected target', 'A diagnosis column is excluded from repair and checked unchanged by ARVA.'],
          ].map(([title, desc], index) => <div className="step-row" key={title}><span className="step-count">{index + 1}</span><div><b>{title}</b><p>{desc}</p></div></div>)}
        </div>}
        <div className="helper-note">Repairs requiring model predictions, such as mixed numeric defects, need the verified ADDA preprocessing pipeline and will return an availability error.</div>
      </Panel>
      <Panel title="Repair this upload" subtitle={job ? `File: ${job.file_name}` : 'Upload a file before requesting repair'}>
        {!job
          ? <EmptyState icon={Wrench} title="No file in this session" description="Upload a CSV before requesting a repair." action={<Link className="button" to="/upload">Upload a dataset</Link>} />
          : <><p className="stat-caption">The API validates and profiles the stored file, writes a separate cleaned CSV and repair history, then runs ARVA preservation checks.</p>
            {error && <div className="error-box section-gap" role="alert">{error}</div>}
            {result && <div className="notice section-gap" role="status"><Check size={16} /><span><b>Repair completed.</b> {job.data_type === 'image_dataset' ? `${result.repair_summary.images_repaired} images repaired; ${result.repair_summary.manual_review} need manual review.` : `${result.repair_summary.cells_repaired} cells changed.`} ARVA: {result.validation.status}. {result.message}</span></div>}
            {result && <div className="step-list section-gap">{job.data_type === 'image_dataset' ? <a className="button" href={getOutputUrl(result.outputs.repaired_images_zip)}><ArrowDownToLine size={14} /> Download repaired images ZIP</a> : <a className="button" href={getOutputUrl(result.outputs.cleaned_csv)}><ArrowDownToLine size={14} /> Download cleaned CSV</a>}<a className="button" href={getOutputUrl(result.outputs.repair_history_csv)}><ArrowDownToLine size={14} /> Download repair history</a></div>}
          </>}
      </Panel>
    </div>
    {result && <Panel title="ARVA checks" subtitle="Results from the generated repaired data" className="section-gap"><div className="step-list">{result.validation.checks.map((check) => <div className="step-row" key={check.name}><span className="step-count">{check.passed ? <Check size={13} /> : '!'}</span><div><b>{check.name.replaceAll('_', ' ')}</b><p>{check.passed ? 'Passed' : 'Failed'}</p></div></div>)}</div></Panel>}
    <div className="section-gap" style={{ display: 'flex', justifyContent: 'flex-end' }}><button className="button primary" onClick={runRepair} disabled={!job || checking}>{checking ? <LoaderCircle size={14} className="spin" /> : <Wrench size={14} />}{checking ? 'Repairing…' : 'Run supported repair'}</button></div>
    <p style={{ textAlign: 'right', fontSize: 10, color: '#98a1b0' }}><Info size={12} style={{ verticalAlign: '-2px' }} /> The original uploaded file is never overwritten.</p>
  </>
}
