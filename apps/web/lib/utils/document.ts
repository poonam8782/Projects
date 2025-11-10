export const getFileTypeLabel = (mimeType: string): string => {
  if (!mimeType) return 'FILE'
  if (mimeType.includes('pdf')) return 'PDF'
  if (mimeType.includes('wordprocessingml')) return 'DOCX'
  if (mimeType.includes('text/plain')) return 'TXT'
  if (mimeType.includes('png')) return 'PNG'
  if (mimeType.includes('jpeg')) return 'JPG'
  return mimeType.split('/')[1]?.toUpperCase() || 'FILE'
}

export const getStatusBadgeVariant = (
  status: string
): 'success' | 'warning' | 'error' | 'outline' => {
  switch (status) {
    case 'extracted':
    case 'embedded':
      return 'success'
    case 'uploaded':
      return 'warning'
    case 'failed':
      return 'error'
    default:
      return 'outline'
  }
}
