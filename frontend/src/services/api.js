import axios from 'axios'

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
        // Clear localStorage; full-page redirect rebuilds Redux store from scratch
        localStorage.removeItem('token')
        localStorage.removeItem('user')
        window.location.href = '/login'
      }
      // If no token, let the error propagate to component (participant 403)
    }
    return Promise.reject(error)
  }
)

export const authAPI = {
  register: (data) => api.post('/auth/register', data),
  login: (data) => api.post('/auth/login', data),
  getMe: () => api.get('/auth/me'),
  verifyEmail: (data) => api.post('/auth/verify-email', data),
  forgotPassword: (data) => api.post('/auth/forgot-password', data),
  resetPassword: (data) => api.post('/auth/reset-password', data),
}

// Quiz API
export const quizAPI = {
  list: (eventId, search) => api.get('/quizzes/', { params: { event_id: eventId, search } }),
  get: (id) => api.get(`/quizzes/${id}`),
  create: (data) => api.post('/quizzes/', data),
  update: (id, data) => api.put(`/quizzes/${id}`, data),
  assignFolder: (id, folderId) => api.put(`/quizzes/${id}/folder`, { folder_id: folderId }),
  delete: (id) => api.delete(`/quizzes/${id}`),
  publish: (id) => api.post(`/quizzes/${id}/publish`),
  publishOffline: (id) => api.post(`/quizzes/${id}/publish-offline`),
  unpublish: (id) => api.post(`/quizzes/${id}/unpublish`),
  duplicate: (id) => api.post(`/quizzes/${id}/duplicate`),
  setTemplate: (id, data) => api.post(`/quizzes/${id}/template`, data),
  listTemplates: () => api.get('/quizzes/template-library'),
  listTemplatesLegacy: () => api.get('/quizzes/templates'),
  useTemplate: (templateQuizId) => api.post(`/quizzes/template-library/${templateQuizId}/use`),
  useTemplateLegacy: (templateQuizId) => api.post(`/quizzes/templates/${templateQuizId}/use`),
  listFolders: () => api.get('/quizzes/folders'),
  createFolder: (data) => api.post('/quizzes/folders', data),
  updateFolder: (id, data) => api.put(`/quizzes/folders/${id}`, data),
  deleteFolder: (id) => api.delete(`/quizzes/folders/${id}`),
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
  uploadImage: (quizId, questionId, file, imageType) => {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('image_type', imageType)
    if (questionId) {
      formData.append('question_id', questionId)
    }
    return api.post(`/quizzes/${quizId}/upload-image`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
  },
  moveTempImages: (quizId, questionId, tempImages) =>
    api.post(`/quizzes/${quizId}/questions/${questionId}/move-temp-images`, tempImages),
  deleteImage: (quizId, questionId, imageType, tempKey) => {
    const params = { image_type: imageType }
    if (tempKey) {
      params.temp_key = tempKey
    }
    if (questionId) {
      params.question_id = questionId
    }
    return api.delete(`/quizzes/${quizId}/image`, { params })
  },
}

// Session API
export const sessionAPI = {
  listSessions: (quizId) => api.get(`/quizzes/${quizId}/sessions`),
  start: (quizId) => api.post('/quizzes/sessions/start', null, { params: { quiz_id: quizId } }),
  join: (data) => api.post('/quizzes/sessions/join', data),
  leave: (sessionToken) => api.post('/quizzes/sessions/leave', null, { params: { session_token: sessionToken } }),
  advance: (sessionId) => api.post(`/quizzes/sessions/${sessionId}/advance`),
  back: (sessionId) => api.post(`/quizzes/sessions/${sessionId}/back`),
  end: (sessionId) => api.post(`/quizzes/sessions/${sessionId}/end`),
  toggleLeaderboard: (sessionId) => api.post(`/quizzes/sessions/${sessionId}/toggle-leaderboard`),
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
      params: sessionToken ? { session_token: sessionToken } : {}
    }),
  getLeaderboard: (sessionId, sessionToken) =>
    api.get(`/quizzes/sessions/${sessionId}/leaderboard`, {
      params: sessionToken ? { session_token: sessionToken } : {}
    }),
  getAudienceResults: (sessionId, sessionToken) =>
    api.get(`/quizzes/sessions/${sessionId}/audience-results`, {
      params: { session_token: sessionToken }
    }),
  getAudienceLeaderboard: (sessionId, sessionToken) =>
    api.get(`/quizzes/sessions/${sessionId}/audience-leaderboard`, {
      params: { session_token: sessionToken }
    }),
  getWhiteboardState: (sessionId) =>
    api.get(`/quizzes/sessions/${sessionId}/whiteboard-state`),
  getPublicWhiteboardState: (sessionId, joinCode) =>
    api.get(`/quizzes/sessions/${sessionId}/whiteboard-state/public`, {
      params: { join_code: joinCode }
    }),
  updateWhiteboardState: (sessionId, data) =>
    api.put(`/quizzes/sessions/${sessionId}/whiteboard-state`, data),
  getPublicWhiteboardEventsUrl: (sessionId, joinCode) =>
    `${API_BASE_URL}/quizzes/sessions/${sessionId}/whiteboard-events/public?join_code=${encodeURIComponent(joinCode)}`,
  exportSession: (sessionId, format) =>
    api.get(`/quizzes/sessions/${sessionId}/export`, {
      params: { format },
      responseType: 'blob',
    }),
}

// Stats API
export const statsAPI = {
  get: () => api.get('/admin/stats'),
  getHistory: (params) => api.get('/admin/stats/history', { params }),
  captureSnapshot: (granularity) => api.post(`/admin/stats/capture?granularity=${granularity}`),
  getFeedback: (params) => api.get('/admin/feedback', { params }),
}

export const platformQuizAPI = {
  list: (params) => api.get('/admin/quizzes', { params }),
}

export const tierConfigAPI = {
  list: () => api.get('/admin/tier-configs'),
  update: (tier, data) => api.put(`/admin/tier-configs/${tier}`, data),
}

export const feedbackAPI = {
  submitParticipant: (sessionToken, data) =>
    api.post('/quizzes/sessions/feedback', data, { params: { session_token: sessionToken } }),
  submitUser: (data) => api.post('/quizzes/feedback', data),
}

// Organization API
export const organizationAPI = {
  listOrganizations: (params) => api.get('/admin/organizations', { params }),
  createOrganization: (data) => api.post('/admin/organizations', data),
  getOrganization: (id) => api.get(`/admin/organizations/${id}`),
  updateOrganization: (id, data) => api.patch(`/admin/organizations/${id}`, data),
  listAdmins: (orgId) => api.get(`/admin/organizations/${orgId}/admins`),
  createAdmin: (data) => api.post('/admin/admin-users', data),
  updateAdminQuota: (adminId, quota) => api.patch(`/admin/admin-users/${adminId}/quota`, { user_quota: quota }),
  getAdminUsage: (adminId) => api.get(`/admin/admin-users/${adminId}/usage`),
}

// Offline Poll API
export const offlinePollAPI = {
  getInfo: (slug) => api.get(`/offline-poll/${slug}`),
  join: (slug, data) => api.post(`/offline-poll/${slug}/join`, data),
  saveAnswer: (slug, data) => api.post(`/offline-poll/${slug}/answer`, data),
  complete: (slug, data) => api.post(`/offline-poll/${slug}/complete`, data),
  getResults: (slug) => api.get(`/offline-poll/${slug}/results`),
}

// Quiz Publish Offline
export const publishOfflinePoll = (id) => api.post(`/quizzes/${id}/publish-offline`)

// Exam API
export const examAPI = {
  getInfo: (slug) => api.get(`/e/${slug}`),
  start: (slug, data) => api.post(`/e/${slug}/start`, data),
  saveAnswer: (slug, data) => api.post(`/e/${slug}/answer`, data),
  submit: (slug, sessionToken) => api.post(`/e/${slug}/submit`, { session_token: sessionToken }),
  getMyResult: (slug, sessionToken) => api.post(`/e/${slug}/result`, { session_token: sessionToken }),
  getResults: (quizId) => api.get(`/quiz/${quizId}/exam-results`),
  publish: (quizId) => api.post(`/quizzes/${quizId}/publish-exam`),
  unpublish: (quizId) => api.post(`/quizzes/${quizId}/unpublish-exam`),
}

// AI Generation API
export const aiAPI = {
  generateQuestions: (data) => api.post('/ai/generate/questions', data),
  generateDistractors: (data) => api.post('/ai/generate/options', data),
  generatePollPrompt: (data) => api.post('/ai/generate/poll-prompt', data),
  rewrite: (data) => api.post('/ai/rewrite', data),
  listModels: () => api.get('/ai/models'),
}

// Language Tracking API
export const languageTrackingAPI = {
  // Update authenticated user's language preference
  updatePreference: (data) => api.post('/user/language-preference', data),
  
  // Log anonymous language change event
  logEvent: (data) => api.post('/language-tracking/event', data),
  
  // Get language usage statistics (admin only)
  getStats: (params) => api.get('/admin/language-stats', { params }),
  
  // Export language stats as CSV (admin only)
  exportStats: (params) => {
    return api.get('/admin/language-stats/export', { 
      params,
      responseType: 'blob'
    })
  },
}

export default api
