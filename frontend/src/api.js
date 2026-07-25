const API_BASE_URL = import.meta.env.DEV
  ? 'http://127.0.0.1:8000'
  : ''

export function apiUrl(path) {
  const normalizedPath = path.startsWith('/')
    ? path
    : `/${path}`

  return `${API_BASE_URL}${normalizedPath}`
}