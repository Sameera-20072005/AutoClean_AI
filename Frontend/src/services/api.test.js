import assert from 'node:assert/strict'
import { afterEach, test } from 'node:test'
import { downloadArtifact, getReport } from './api.js'
import { artifactIsDownloadable, reportPageStatus } from '../pages/reportsUtils.js'

const originals = {
  fetch: globalThis.fetch,
  document: globalThis.document,
  createObjectURL: URL.createObjectURL,
  revokeObjectURL: URL.revokeObjectURL,
}

afterEach(() => {
  globalThis.fetch = originals.fetch
  globalThis.document = originals.document
  URL.createObjectURL = originals.createObjectURL
  URL.revokeObjectURL = originals.revokeObjectURL
})

test('reports status exposes loading, backend result, and no-job states', () => {
  assert.equal(reportPageStatus({ file_id: 'abc' }, true, null), 'Loading reports')
  assert.equal(reportPageStatus({ file_id: 'abc' }, false, { status: 'partial' }), 'partial')
  assert.equal(reportPageStatus(null, false, null), 'No active file')
})

test('downloads stay disabled until a generated backend URL exists', () => {
  assert.equal(artifactIsDownloadable({ status: 'not_generated', download_url: null }), false)
  const id = '12345678901234567890123456789012'
  assert.equal(artifactIsDownloadable({ status: 'generated', download_url: `/api/outputs/${id}/cleaned` }), true)
  assert.equal(artifactIsDownloadable({ status: 'generated', download_url: `/api/outputs/${id}/repaired-images` }), true)
  assert.equal(artifactIsDownloadable({ status: 'generated', download_url: `/api/outputs/${id}/image-history` }), true)
  assert.equal(artifactIsDownloadable({ status: 'generated', download_url: 'C:\\private\\report.json' }), false)
})

test('getReport remains pending while the report request is loading', async () => {
  let resolveFetch
  globalThis.fetch = () => new Promise((resolve) => { resolveFetch = resolve })
  let settled = false
  const pending = getReport('12345678901234567890123456789012').then((value) => {
    settled = true
    return value
  })
  await Promise.resolve()
  assert.equal(settled, false)
  resolveFetch({ ok: true, json: async () => ({ status: 'partial' }) })
  assert.deepEqual(await pending, { status: 'partial' })
  assert.equal(settled, true)
})

test('downloadArtifact surfaces backend errors instead of starting a download', async () => {
  globalThis.fetch = async () => ({ ok: false, status: 404, json: async () => ({ error: { code: 'output_not_found', message: 'Output not found.' } }) })
  await assert.rejects(downloadArtifact('/api/outputs/12345678901234567890123456789012/cleaned', 'cleaned.csv'), /Output not found/)
})

test('downloadArtifact creates a browser download for a valid generated output', async () => {
  let clicked = false
  let removed = false
  let appended = false
  globalThis.fetch = async () => ({ ok: true, blob: async () => new Blob(['real output']) })
  URL.createObjectURL = () => 'blob:test-report'
  URL.revokeObjectURL = () => {}
  globalThis.document = {
    createElement: () => ({ style: {}, click: () => { clicked = true }, remove: () => { removed = true } }),
    body: { appendChild: () => { appended = true } },
  }
  await downloadArtifact('/api/outputs/12345678901234567890123456789012/quality-report', 'quality.json')
  assert.equal(appended, true)
  assert.equal(clicked, true)
  assert.equal(removed, true)
})
