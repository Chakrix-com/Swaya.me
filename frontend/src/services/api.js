import axios from 'axios'
import { store } from '../store/store'
import { logout } from '../store/authSlice'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Add auth token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Handle expired token responses
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // Only redirect to login for auth failures with tokens (host requests)
    // Let 403 pass through for participant session invalidation
    if (error.response && (error.response.status === 401 || error.response.status === 403)) {
      // Check if this was an authenticated request (has token)
      const hasAuthToken = error.config?.headers?.Authorization
      
      if (hasAuthToken) {
        // Host authentication failed - redirect to login
        localStorage.removeItem('token')
        store.dispatch(logout())
        window.location.href = '/login'
      }
      // If no token, let the error propagate to component (participant 403)
    }
    return Promise.reject(error)
  }
)

// Auth API
export const authAPI = {
  register: (data) => api.post('/auth/register', data),
  login: (data) => api.post('/auth/login', data),
  getMe: () => api.get('/auth/me'),
}

// Quiz API
export const quizAPI = {
  list: (eventId) => api.get('/quizzes/', { params: { event_id: eventId } }),
  get: (id) => api.get(`/quizzes/${id}`),
  create: (data) => api.post('/quizzes/', data),
  update: (id, data) => api.put(`/quizzes/${id}`, data),
  delete: (id) => api.delete(`/quizzes/${id}`),
  publish: (id) => api.post(`/quizzes/${id}/publish`),
  unpublish: (id) => api.post(`/quizzes/${id}/unpublish`),
}

// Question API
export const questionAPI = {
  add: (quizId, data) => api.post(`/quizzes/${quizId}/questions`, data),
  update: (id, data) => api.put(`/quizzes/questions/${id}`, data),
  delete: (id) => api.delete(`/quizzes/questions/${id}`),
  getWordCloudResults: (questionId, sessionId) => 
    api.get(`/quizzes/questions/${questionId}/word-cloud-results`, {
      params: { session_id: sessionId }
    }),
}

// Session API
export const sessionAPI = {
  start: (quizId) => api.post('/quizzes/sessions/start', null, { params: { quiz_id: quizId } }),
  join: (data) => api.post('/quizzes/sessions/join', data),
  advance: (sessionId) => api.post(`/quizzes/sessions/${sessionId}/advance`),
  back: (sessionId) => api.post(`/quizzes/sessions/${sessionId}/back`),
  end: (sessionId) => api.post(`/quizzes/sessions/${sessionId}/end`),
  submitAnswer: (sessionToken, data) => 
    api.post('/quizzes/sessions/submit-answer', data, { 
      params: { session_token: sessionToken } 
    }),
  submitWordCloudAnswer: (sessionToken, data) => 
    api.post('/quizzes/sessions/submit-word-cloud', data, { 
      params: { session_token: sessionToken } 
    }),
  getResults: (sessionId, sessionToken) => 
    api.get(`/quizzes/sessions/${sessionId}/results`, { 
      params: { session_token: sessionToken } 
    }),
}

export default api
