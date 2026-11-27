export const MAX_UPLOAD_BYTES = 25 * 1024 * 1024

export function formatFileSize(size) {
  return size < 1024 * 1024
    ? `${(size / 1024).toFixed(1)} KB`
    : `${(size / 1024 / 1024).toFixed(2)} MB`
}

export function getFileExtension(name = '') {
  return name.split('.').pop().toLowerCase()
}
