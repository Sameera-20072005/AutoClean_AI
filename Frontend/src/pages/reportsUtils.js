export function reportPageStatus(job, loading, report) {
  if (loading) return 'Loading reports'
  return report?.status || (job ? 'Not checked' : 'No active file')
}

export function artifactIsDownloadable(artifact) {
  return artifact?.status === 'generated' && typeof artifact.download_url === 'string' && /^\/api\/outputs\/[0-9a-f]{32}\/(cleaned|history|quality-report|validation-report|repaired-images|image-history)$/.test(artifact.download_url)
}
