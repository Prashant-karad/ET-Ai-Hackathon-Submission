const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

async function request(path, options = {}) {
  const response = await fetch(`${BASE_URL}${path}`, options)
  const payload = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(payload.detail || 'Something went wrong. Please try again.')
  return payload
}

export const api = {
  dashboard: () => request('/api/dashboard'),
  documents: () => request('/api/documents'),
  upload: (file) => {
    const data = new FormData()
    data.append('file', file)
    return request('/api/documents/upload', { method: 'POST', body: data })
  },
  generateCard: (body) => request('/api/knowledge/generate', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }),
  saveCard: (body) => request('/api/knowledge/save', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }),
  ask: (question) => request('/api/ask', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ question }) }),
  seed: () => request('/api/demo/seed', { method: 'POST' }),
}
