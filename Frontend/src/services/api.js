const API_URL = import.meta.env?.VITE_API_URL || 'http://localhost:8000'

export function getOutputUrl(path) {
  return `${API_URL}${path}`
}

async function request(path, options = {}) {
  let response
  try {
    response = await fetch(`${API_URL}${path}`, options)
  } catch {
    throw new Error('Could not reach the AutoClean API. Confirm that the backend is running.')
  }
  const payload = await response.json().catch(() => ({}))
  if (!response.ok) {
    const error = new Error(payload?.error?.message || `Request failed (${response.status}).`)
    error.status = response.status
    error.code = payload?.error?.code || 'request_failed'
    throw error
  }
  return payload
}

export function getBackendHealth(signal) {
  return request('/api/health', { signal })
}

export function getDashboard(signal) {
  return request('/api/dashboard', { signal })
}

export function uploadDataset(file) {
  const form = new FormData()
  form.append('file', file)
  return request('/api/upload', { method: 'POST', body: form })
}

export function uploadImageDataset(manifest, imagesZip) {
  const form = new FormData()
  form.append('manifest', manifest)
  form.append('images_zip', imagesZip)
  return request('/api/upload/image-dataset', { method: 'POST', body: form })
}

export function getAnalysis(fileId, signal) {
  return request(`/api/analysis/${encodeURIComponent(fileId)}`, { signal })
}

export function requestRepair(fileId) {
  return request(`/api/repair/${encodeURIComponent(fileId)}`, { method: 'POST' })
}

export function getValidation(fileId, signal) {
  return request(`/api/validation/${encodeURIComponent(fileId)}`, { signal })
}

export function getReport(fileId, signal) {
  return request(`/api/reports/${encodeURIComponent(fileId)}`, { signal })
}

export async function downloadArtifact(path, filename) {
  if (typeof path !== 'string' || !/^\/api\/outputs\/[0-9a-f]{32}\/(cleaned|history|quality-report|validation-report|repaired-images|image-history)$/.test(path)) {
    throw new Error('The API returned an invalid download reference.')
  }
  let response
  try {
    response = await fetch(`${API_URL}${path}`)
  } catch {
    throw new Error('Could not reach the AutoClean API to download this artifact.')
  }
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}))
    const error = new Error(payload?.error?.message || `Download failed (${response.status}).`)
    error.status = response.status
    error.code = payload?.error?.code || 'download_failed'
    throw error
  }
  const blob = await response.blob()
  const objectUrl = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = objectUrl
  anchor.download = filename
  anchor.style.display = 'none'
  document.body.appendChild(anchor)
  try {
    anchor.click()
  } finally {
    anchor.remove()
    setTimeout(() => URL.revokeObjectURL(objectUrl), 1000)
  }
}
