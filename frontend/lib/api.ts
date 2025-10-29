import axios from 'axios'

const API_URL = process.env.API_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: API_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor for logging
api.interceptors.request.use(
  (config) => {
    console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`)
    return config
  },
  (error) => {
    console.error('API Request Error:', error)
    return Promise.reject(error)
  }
)

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => {
    return response
  },
  (error) => {
    console.error('API Response Error:', error.response?.data || error.message)
    return Promise.reject(error)
  }
)

// Training API
export const trainingAPI = {
  start: () => api.post('/api/train/start'),
  stop: () => api.post('/api/train/stop'),
  status: () => api.get('/api/train/status'),
  sessions: () => api.get('/api/train/sessions'),
}

// Live API
export const liveAPI = {
  start: () => api.post('/api/live/start'),
  stop: () => api.post('/api/live/stop'),
  trust: () => api.get('/api/live/trust'),
  stats: () => api.get('/api/live/stats'),
  anomalies: () => api.get('/api/live/anomalies'),
  status: () => api.get('/api/live/status'),
}

// Events API
export const eventsAPI = {
  create: (event: any) => api.post('/api/events/', event),
  get: (params?: any) => api.get('/api/events/', { params }),
  recent: (limit = 50) => api.get(`/api/events/recent?limit=${limit}`),
}

// Admin API
export const adminAPI = {
  markNormal: (anomalyId: number) => api.post('/api/admin/mark_normal', { anomaly_id: anomalyId }),
  reset: () => api.post('/api/admin/reset'),
  exit: () => api.post('/api/admin/exit'),
  anomalies: (params?: any) => api.get('/api/admin/anomalies', { params }),
  stats: () => api.get('/api/admin/stats'),
  systemStatus: () => api.get('/api/admin/system_status'),
  performanceMetrics: () => api.get('/api/admin/performance_metrics'),
  toggleTestMode: (enabled: boolean) => api.post('/api/admin/toggle_test_mode', { enabled }),
  runModelTest: (params: any) => api.post('/api/admin/run_model_test', params),
  generateTestData: () => api.post('/api/admin/generate_test_data'),
}

// Health check
export const healthAPI = {
  check: () => api.get('/health'),
}

export default api
