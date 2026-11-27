import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { AlertCircle, Archive, CheckCircle2, FileImage, FileSpreadsheet, Image as ImageIcon, LoaderCircle, Trash2, UploadCloud, X } from 'lucide-react'
import { Link } from 'react-router-dom'
import { EmptyState, PageHeader, Panel } from '../components/Common.jsx'
import { useJob } from '../context/JobContext.jsx'
import { uploadDataset, uploadImageDataset } from '../services/api.js'
import { formatFileSize, getFileExtension, MAX_UPLOAD_BYTES } from '../utils/files.js'
import './UploadPage.css'

const accepts = { tabular: ['csv'], image: ['png', 'jpg', 'jpeg'] }

export default function UploadPage() {
  const [mode, setMode] = useState('tabular')
  const [file, setFile] = useState(null)
  const [error, setError] = useState('')
  const [drag, setDrag] = useState(false)
  const [csv, setCsv] = useState(null)
  const [imageUrl, setImageUrl] = useState('')
  const [uploading, setUploading] = useState(false)
  const [manifest, setManifest] = useState(null)
  const [imagesZip, setImagesZip] = useState(null)
  const [manifestError, setManifestError] = useState('')
  const [zipError, setZipError] = useState('')
  const [draggingField, setDraggingField] = useState('')
  const [uploaded, setUploaded] = useState(false)
  const manifestInput = useRef(null)
  const zipInput = useRef(null)
  const input = useRef(null)
  const navigate = useNavigate()
  const { setJob } = useJob()

  useEffect(() => {
    if (!file || mode !== 'image') { setImageUrl(''); return }
    const url = URL.createObjectURL(file)
    setImageUrl(url)
    return () => URL.revokeObjectURL(url)
  }, [file, mode])

  const clear = () => {
    setFile(null); setError(''); setCsv(null); setManifest(null); setImagesZip(null); setManifestError(''); setZipError(''); setUploaded(false)
    if (input.current) input.current.value = ''
    if (manifestInput.current) manifestInput.current.value = ''
    if (zipInput.current) zipInput.current.value = ''
  }

  const chooseDatasetFile = (kind, nextFile) => {
    if (!nextFile) return
    const isManifest = kind === 'manifest'
    const validExtension = getFileExtension(nextFile.name) === (isManifest ? 'csv' : 'zip')
    const setFieldError = isManifest ? setManifestError : setZipError
    if (!validExtension) { setFieldError(`Choose a .${isManifest ? 'csv' : 'zip'} file.`); return }
    if (nextFile.size > MAX_UPLOAD_BYTES) { setFieldError('File exceeds the 25 MB limit. Choose a smaller file.'); return }
    setFieldError(''); setUploaded(false)
    if (isManifest) setManifest(nextFile); else setImagesZip(nextFile)
  }

  const removeDatasetFile = (kind) => {
    if (kind === 'manifest') { setManifest(null); setManifestError(''); if (manifestInput.current) manifestInput.current.value = '' }
    else { setImagesZip(null); setZipError(''); if (zipInput.current) zipInput.current.value = '' }
    setUploaded(false)
  }

  const choose = (nextFile) => {
    if (!nextFile) return
    setError(''); setCsv(null)
    const extension = getFileExtension(nextFile.name)
    if (!accepts[mode].includes(extension)) {
      setFile(null)
      setError(`Unsupported file type. Choose ${mode === 'tabular' ? '.csv' : '.png, .jpg or .jpeg'}.`)
      return
    }
    if (nextFile.size > MAX_UPLOAD_BYTES) {
      setFile(null); setError('File exceeds the 25 MB limit. Choose a smaller file.'); return
    }
    setFile(nextFile)
    if (mode === 'tabular') {
      const reader = new FileReader()
      reader.onload = () => {
        const rows = String(reader.result || '').split(/\r?\n/).filter(Boolean)
        const columns = (rows[0] || '').split(',')
        setCsv({ rowCount: Math.max(rows.length - 1, 0), columns, sample: rows.slice(0, 4).map((row) => row.split(',')) })
      }
      reader.onerror = () => setError('Could not preview this CSV file. Try another file.')
      reader.readAsText(nextFile.slice(0, 150000))
    }
  }

  const switchMode = (nextMode) => { setMode(nextMode); clear() }
  const onDrop = (event) => { event.preventDefault(); setDrag(false); choose(event.dataTransfer.files?.[0]) }
  const startAnalysis = async () => {
    if ((mode === 'image_dataset' ? !manifest || !imagesZip : !file) || uploading) return
    setUploading(true); setError('')
    try {
      const uploaded = mode === 'image_dataset' ? await uploadImageDataset(manifest, imagesZip) : await uploadDataset(file)
      setUploaded(true)
      setJob(uploaded)
      navigate('/analysis')
    } catch (uploadError) {
      setError(uploadError.message || 'Upload failed. Please try again.')
    } finally { setUploading(false) }
  }

  return <>
    <PageHeader eyebrow="NEW DATASET" title="Upload dataset" description="Upload a tabular CSV, one image, or an image manifest together with its ZIP archive." />
    <div className="upload-tabs" role="tablist" aria-label="Upload file type">
      <button className={`upload-tab ${mode === 'tabular' ? 'active' : ''}`} role="tab" aria-selected={mode === 'tabular'} onClick={() => switchMode('tabular')}><FileSpreadsheet size={15} />Tabular CSV</button>
      <button className={`upload-tab ${mode === 'image' ? 'active' : ''}`} role="tab" aria-selected={mode === 'image'} onClick={() => switchMode('image')}><ImageIcon size={15} />Image</button>
      <button className={`upload-tab ${mode === 'image_dataset' ? 'active' : ''}`} role="tab" aria-selected={mode === 'image_dataset'} onClick={() => switchMode('image_dataset')}><FileStackIcon />Image dataset</button>
    </div>
    <div className="grid two">
      <Panel title="Choose a file" subtitle={mode === 'tabular' ? 'CSV files up to 25 MB' : mode === 'image_dataset' ? 'A CSV manifest and ZIP archive, up to 25 MB each' : 'PNG, JPG or JPEG files up to 25 MB'}>
        {mode !== 'image_dataset' && <input ref={input} type="file" hidden accept={mode === 'tabular' ? '.csv,text/csv' : '.png,.jpg,.jpeg,image/png,image/jpeg'} onChange={(event) => choose(event.target.files?.[0])} aria-label={`Choose ${mode === 'tabular' ? 'CSV' : 'image'} file`} />}
        {mode === 'image_dataset' && <>
          <div className="dataset-upload-grid">
            {[
              { key: 'manifest', title: 'CSV Manifest', hint: 'Drop a .csv file here or browse your files', icon: FileSpreadsheet, accept: '.csv,text/csv', file: manifest, error: manifestError, input: manifestInput, button: 'Browse CSV' },
              { key: 'zip', title: 'Images ZIP Archive', hint: 'Drop a .zip archive here or browse your files', icon: Archive, accept: '.zip,application/zip', file: imagesZip, error: zipError, input: zipInput, button: 'Browse ZIP' },
            ].map(({ key, title, hint, icon: Icon, accept, file: selected, error: fieldError, input: fileInput, button }) => {
              const isDragging = draggingField === key
              const status = fieldError || (error && mode === 'image_dataset') ? 'Error' : uploading ? 'Uploading' : uploaded ? 'Uploaded' : selected ? 'Selected' : 'Empty'
              return <div key={key} className={`dataset-upload-card ${isDragging ? 'dragging' : ''} ${fieldError ? 'has-error' : ''}`} onDragOver={(event) => { event.preventDefault(); setDraggingField(key) }} onDragLeave={(event) => { if (!event.currentTarget.contains(event.relatedTarget)) setDraggingField('') }} onDrop={(event) => { event.preventDefault(); setDraggingField(''); chooseDatasetFile(key, event.dataTransfer.files?.[0]) }}>
                <div className="dataset-upload-card-top"><span className="dataset-upload-icon"><Icon size={19} /></span><span className={`dataset-upload-status ${status.toLowerCase()}`}><i />{status}</span></div>
                <h3>{title}</h3><p className="dataset-upload-hint">{hint}</p>
                <input ref={fileInput} type="file" accept={accept} onChange={(event) => chooseDatasetFile(key, event.target.files?.[0])} aria-label={`Choose ${title}`} />
                {selected ? <div className="dataset-selected-file"><span className="dataset-selected-file-icon"><Icon size={15} /></span><span className="dataset-selected-meta"><b title={selected.name}>{selected.name}</b><small>{formatFileSize(selected.size)}</small></span><button type="button" className="dataset-remove" onClick={() => removeDatasetFile(key)} aria-label={`Remove ${title}`} title="Remove file"><X size={16} /></button><button type="button" className="dataset-replace" onClick={() => fileInput.current?.click()}>Replace</button></div> : <button type="button" className="button dataset-browse" onClick={() => fileInput.current?.click()}><UploadCloud size={15} />{button}</button>}
                {fieldError && <p className="dataset-field-error" role="alert"><AlertCircle size={13} />{fieldError}</p>}
                {uploading && <div className="dataset-progress" role="progressbar" aria-label={`Uploading ${title}`}><span /></div>}
              </div>
            })}
          </div>
          <p className="dataset-requirement"><CheckCircle2 size={14} /> Both files are required. Each file must be under 25 MB.</p>
        </>}
        {mode !== 'image_dataset' && <div className={`dropzone ${drag ? 'dragging' : ''}`} onDragOver={(event) => { event.preventDefault(); setDrag(true) }} onDragLeave={() => setDrag(false)} onDrop={onDrop}>
          <div><div className="dropzone-icon"><UploadCloud size={22} /></div><h3>{`Drag and drop your ${mode === 'tabular' ? 'CSV' : 'image'} here`}</h3><p>Or browse files on your device</p><button className="button" type="button" onClick={() => input.current?.click()}>Browse files</button></div>
        </div>}
        {error && <div className="error-box" role="alert"><AlertCircle size={15} />{error}</div>}
        {file && <div className="file-info"><span className="stat-icon">{mode === 'tabular' ? <FileSpreadsheet size={16} /> : <FileImage size={16} />}</span><div className="file-meta"><b title={file.name}>{file.name}</b><span>{formatFileSize(file.size)}</span></div><button className="icon-button" type="button" onClick={clear} aria-label="Remove selected file"><Trash2 size={15} /></button></div>}
        <div className="helper-note" style={{ marginTop: 14 }}>The file is sent to this local backend and stored under a generated server ID. Do not upload sensitive personal or medical data to an unsecured prototype.</div>
      </Panel>
      <Panel title="Local preview" subtitle="Preview before sending the file to the backend">
        {mode === 'image_dataset' ? <div className="step-list"><p>{manifest ? `Manifest: ${manifest.name} (${formatFileSize(manifest.size)})` : 'Choose a manifest CSV.'}</p><p>{imagesZip ? `Images: ${imagesZip.name} (${formatFileSize(imagesZip.size)})` : 'Choose the ZIP archive containing the images.'}</p></div> : !file ? <EmptyState icon={mode === 'tabular' ? FileSpreadsheet : ImageIcon} title="Select a file to preview" description="Basic file details will appear here after you choose a supported file." /> : mode === 'tabular' ? <>
          <div className="grid equal"><div className="workflow-step"><b>{csv?.rowCount ?? '…'}</b><p>Rows in local preview</p></div><div className="workflow-step"><b>{csv?.columns.length ?? '…'}</b><p>Columns in local preview</p></div></div>
          <div className="card-title" style={{ marginTop: 16 }}><h2>Column names</h2><span className="badge">First row</span></div>
          <p style={{ color: '#6e7a91', fontSize: 11, lineHeight: 1.8 }}>{csv?.columns.slice(0, 8).join(' · ') || 'Reading file…'}</p>
          {csv?.sample?.length > 1 && <div className="table-wrap"><table className="table"><thead><tr>{csv.sample[0].slice(0, 5).map((cell, index) => <th key={index}>{cell || `Column ${index + 1}`}</th>)}</tr></thead><tbody>{csv.sample.slice(1, 4).map((row, rowIndex) => <tr key={rowIndex}>{row.slice(0, 5).map((cell, columnIndex) => <td key={columnIndex}>{cell || '—'}</td>)}</tr>)}</tbody></table></div>}
          <p className="stat-caption">Lightweight local text preview only; the backend performs the actual CSV parse and profile.</p>
        </> : <><div className="preview-box"><img src={imageUrl} alt={`Selected file preview: ${file.name}`} /><div className="preview-caption">{file.name} · {formatFileSize(file.size)} · {file.type || 'Image format'}</div></div></>}
      </Panel>
    </div>
    <div className="section-gap" style={{ display: 'flex', justifyContent: 'flex-end', gap: 9 }}><button className="button" onClick={clear} disabled={(!file && !manifest && !imagesZip) || uploading}>Clear selection</button><button className="button primary" onClick={startAnalysis} disabled={(mode === 'image_dataset' ? !manifest || !imagesZip : !file) || uploading}>{uploading && <LoaderCircle size={14} className="spin" />}{uploading ? 'Uploading…' : 'Upload and analyze'}</button></div>
    <p style={{ textAlign: 'right', fontSize: 10, color: '#98a1b0' }}>ADDA model predictions may remain unavailable until the Colab preprocessing pipeline is restored. <Link to="/about" style={{ color: '#536ee5' }}>See project status</Link></p>
  </>
}

function FileStackIcon() { return <FileSpreadsheet size={15} /> }
