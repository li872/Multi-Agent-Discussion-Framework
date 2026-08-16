export function auditApiBase(): string {
  if (window.location.port === '81' || window.location.port === '5174') {
    return '/api/v1'
  }
  return '/audit/api/v1'
}

export function auditBasename(): string {
  if (window.location.port === '81' || window.location.port === '5174') {
    return ''
  }
  if (window.location.pathname.startsWith('/audit')) {
    return '/audit'
  }
  return ''
}

export function auditLoginPath(): string {
  return `${auditBasename()}/login`
}
