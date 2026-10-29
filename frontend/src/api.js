const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
  });
  if (!response.ok) {
    let detail = `Request failed with HTTP ${response.status}`;
    try {
      const body = await response.json();
      detail = body.detail || detail;
    } catch {
      // Keep the status message if the server returns non-JSON.
    }
    throw new Error(detail);
  }
  return response.json();
}

export const api = {
  health: () => request('/api/health'),
  overview: () => request('/api/overview'),
  testCases: () => request('/api/test-cases'),
  runs: () => request('/api/runs?limit=10'),
  runSuite: () => request('/api/runs', { method: 'POST' }),
  runDetail: (id) => request(`/api/runs/${id}`),
  clearRuns: () => request('/api/runs', { method: 'DELETE' }),
};
