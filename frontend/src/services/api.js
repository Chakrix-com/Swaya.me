import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

// Default timeout so a hung request fails visibly instead of leaving a
// spinner/disabled button stuck forever. AI-generation and document-export
// calls override this per-request with LONG_TIMEOUT since they legitimately
// take longer than everyday CRUD calls.
const DEFAULT_TIMEOUT = 45000
const LONG_TIMEOUT = 120000

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,  // send HttpOnly access_token cookie automatically
  timeout: DEFAULT_TIMEOUT,
})

// Handle expired/invalid session responses
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // 401 = cookie/token is definitively invalid → clear state and redirect to login
    // 403 passes through: could be permission denied or participant session invalidation
    if (error.response?.status === 401) {
      localStorage.removeItem('user')
      // Don't redirect for session probe (/auth/me) — App.jsx handles that gracefully.
      // Don't redirect if already on /login to avoid an infinite reload loop.
      const isProbe = error.config?.url?.includes('/auth/me')
      const alreadyOnLogin = window.location.pathname === '/login'
      if (!isProbe && !alreadyOnLogin) {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

export const authAPI = {
  register: (data) => api.post('/auth/register', data),
  login: (data) => api.post('/auth/login', data),
  logout: () => api.post('/auth/logout'),
  getMe: () => api.get('/auth/me'),
  verifyEmail: (data) => api.post('/auth/verify-email', data),
  forgotPassword: (data) => api.post('/auth/forgot-password', data),
  resetPassword: (data) => api.post('/auth/reset-password', data),
  getMyLimits: () => api.get('/auth/my-limits'),
  getTierPlans: () => api.get('/auth/tier-plans'),
  googleCallback: (code, state) => api.get('/auth/google/callback', { params: { code, state } }),
  getTenantUsers: () => api.get('/users', { params: { per_page: 100 } }),
}

// Quiz API
export const quizAPI = {
  list: (eventId, search, includeArchived) => api.get('/quizzes/', { params: { event_id: eventId, search, include_archived: includeArchived || undefined } }),
  get: (id) => api.get(`/quizzes/${id}`),
  create: (data) => api.post('/quizzes/', data),
  update: (id, data) => api.put(`/quizzes/${id}`, data),
  assignFolder: (id, folderId) => api.put(`/quizzes/${id}/folder`, { folder_id: folderId }),
  delete: (id) => api.delete(`/quizzes/${id}`),
  publish: (id) => api.post(`/quizzes/${id}/publish`),
  publishOffline: (id) => api.post(`/quizzes/${id}/publish-offline`),
  unpublish: (id) => api.post(`/quizzes/${id}/unpublish`),
  archive: (id) => api.post(`/quizzes/${id}/archive`),
  unarchive: (id) => api.post(`/quizzes/${id}/unarchive`),
  duplicate: (id) => api.post(`/quizzes/${id}/duplicate`),
  setTemplate: (id, data) => api.post(`/quizzes/${id}/template`, data),
  listPublicTemplates: () => api.get('/quizzes/public-templates'),
  listTemplates: () => api.get('/quizzes/template-library'),
  listTemplatesLegacy: () => api.get('/quizzes/templates'),
  useTemplate: (templateQuizId) => api.post(`/quizzes/template-library/${templateQuizId}/use`),
  useTemplateLegacy: (templateQuizId) => api.post(`/quizzes/templates/${templateQuizId}/use`),
  listFolders: () => api.get('/quizzes/folders'),
  createFolder: (data) => api.post('/quizzes/folders', data),
  updateFolder: (id, data) => api.put(`/quizzes/folders/${id}`, data),
  deleteFolder: (id) => api.delete(`/quizzes/folders/${id}`),
  getFolderShares: (id) => api.get(`/quizzes/folders/${id}/shares`),
  updateFolderShares: (id, data) => api.put(`/quizzes/folders/${id}/shares`, data),
  getImportTemplate: () => api.get('/quizzes/import/template', { responseType: 'blob' }),
  exportDraftToExcel: (data) => api.post('/quizzes/import/export-draft', data, { responseType: 'blob' }),
  validateImport: (file) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post('/quizzes/import/validate', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },
  finalizeImport: (data) => api.post('/quizzes/import/finalize', data),
}

// Question API
export const questionAPI = {
  add: (quizId, data) => api.post(`/quizzes/${quizId}/questions`, data),
  update: (id, data) => api.put(`/quizzes/questions/${id}`, data),
  delete: (id) => api.delete(`/quizzes/questions/${id}`),
  duplicate: (quizId, questionId) => api.post(`/quizzes/${quizId}/questions/${questionId}/duplicate`),
  reorder: (quizId, questionOrders) => api.put(`/quizzes/${quizId}/questions/reorder`, { question_orders: questionOrders }),
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
  listAllSessions: (params) => api.get('/quizzes/sessions/all', { params }),
  homeStats: () => api.get('/quizzes/sessions/home-stats'),
  lookup: (joinCode) => api.get('/quizzes/sessions/lookup', { params: { join_code: joinCode } }),
  start: (quizId) => api.post('/quizzes/sessions/start', null, { params: { quiz_id: quizId } }),
  join: (data) => api.post('/quizzes/sessions/join', data),
  leave: (sessionToken) => api.post('/quizzes/sessions/leave', null, { params: { session_token: sessionToken } }),
  advance: (sessionId) => api.post(`/quizzes/sessions/${sessionId}/advance`),
  closeQuestion: (sessionId) => api.post(`/quizzes/sessions/${sessionId}/close-question`),
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
  getReactions: (sessionId) =>
    api.get(`/quizzes/sessions/${sessionId}/reactions`),
  listParticipants: (sessionId) =>
    api.get(`/quizzes/sessions/${sessionId}/participants-list`),
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
      timeout: LONG_TIMEOUT,
    }),
  evaluateCode: (sessionId, questionId) =>
    api.post(`/quizzes/sessions/${sessionId}/questions/${questionId}/evaluate-code`),
  getCodeAnswers: (sessionId, questionId) =>
    api.get(`/quizzes/sessions/${sessionId}/questions/${questionId}/code-answers`),
}

// Stats API
export const statsAPI = {
  get: () => api.get('/admin/stats'),
  getHistory: (params) => api.get('/admin/stats/history', { params }),
  captureSnapshot: (granularity) => api.post(`/admin/stats/capture?granularity=${granularity}`),
  getFeedback: (params) => api.get('/admin/feedback', { params }),
  getWeeklyActiveHosts: (days = 7) => api.get('/admin/stats/weekly-active-hosts', { params: { days } }),
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
  requestOtp: (slug, data) => api.post(`/e/${slug}/request-otp`, data),
  start: (slug, data) => api.post(`/e/${slug}/start`, data),
  saveAnswer: (slug, data) => api.post(`/e/${slug}/answer`, data),
  runCode: (slug, data) => api.post(`/e/${slug}/run-code`, data),
  submit: (slug, sessionToken) => api.post(`/e/${slug}/submit`, { session_token: sessionToken }),
  getMyResult: (slug, sessionToken) => api.post(`/e/${slug}/result`, { session_token: sessionToken }),
  getResults: (quizId) => api.get(`/quiz/${quizId}/exam-results`),
  getParticipantDetail: (quizId, participantId) => api.get(`/quiz/${quizId}/exam-results/participant/${participantId}`),
  analyzeResults: (quizId, customPrompt) =>
    api.post(`/quiz/${quizId}/analyze-results`, customPrompt ? { custom_prompt: customPrompt } : {}, { timeout: LONG_TIMEOUT }),
  publish: (quizId, freshStart = false) => api.post(`/quizzes/${quizId}/publish-exam`, null, { params: freshStart ? { fresh_start: true } : {} }),
  unpublish: (quizId) => api.post(`/quizzes/${quizId}/unpublish-exam`),
  sendParticipantEmails: (quizId, senderName) =>
    api.post(`/quiz/${quizId}/send-participant-emails`, senderName ? { sender_name: senderName } : {}),
  getCertMeta: (token) => api.get(`/exam/cert-meta/${token}`),
  generateInterviewSheet: (quizId, participantId) =>
    api.post(`/quiz/${quizId}/participants/${participantId}/interview-sheet`, null, { timeout: LONG_TIMEOUT }),
  downloadInterviewSheet: (quizId, participantId, data) =>
    api.post(`/quiz/${quizId}/participants/${participantId}/interview-sheet/download`, data, { responseType: 'blob', timeout: LONG_TIMEOUT }),
  emailInterviewSheet: (quizId, participantId, data) =>
    api.post(`/quiz/${quizId}/participants/${participantId}/interview-sheet/email`, data, { timeout: LONG_TIMEOUT }),
}

// AI Generation API
export const aiAPI = {
  generateQuestions: (data) => api.post('/ai/generate/questions', data, { timeout: LONG_TIMEOUT }),
  generateDistractors: (data) => api.post('/ai/generate/options', data, { timeout: LONG_TIMEOUT }),
  generatePollPrompt: (data) => api.post('/ai/generate/poll-prompt', data, { timeout: LONG_TIMEOUT }),
  rewrite: (data) => api.post('/ai/rewrite', data, { timeout: LONG_TIMEOUT }),
  listModels: () => api.get('/ai/models'),
  extractText: (file, url) => {
    const form = new FormData()
    if (file) form.append('file', file)
    if (url) form.append('url', url)
    return api.post('/ai/extract-text', form, { headers: { 'Content-Type': 'multipart/form-data' }, timeout: LONG_TIMEOUT })
  },
  streamGenerateQuestions: async (data, onQuestion, onDone, signal) => {
    const base = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'
    const res = await fetch(`${base}/ai/generate/questions/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify(data),
      signal,
    })
    if (!res.ok) {
      const errBody = await res.json().catch(() => ({}))
      throw new Error(errBody.detail || `HTTP ${res.status}`)
    }
    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() ?? ''
      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        try {
          const item = JSON.parse(line.slice(6))
          if (item.error) throw new Error(item.error)
          if (item.done) {
            onDone(item)
          } else {
            onQuestion(item)
          }
        } catch (e) {
          if (e.message && !e.message.startsWith('JSON')) throw e
        }
      }
    }
  },
}

export const appFeedbackAPI = {
  submit: (data) => api.post('/feedback/app', data),
  listAppFeedback: (params) => api.get('/admin/app-feedback', { params }),
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

export const proctoringAPI = {
  getConfig: (quizId, sessionToken) =>
    api.get(`/proctoring/config/${quizId}`, {
      headers: sessionToken ? { 'X-Session-Token': sessionToken } : {},
    }),
  initSession: (body, sessionToken) =>
    api.post('/proctoring/session/init', body, {
      headers: sessionToken ? { 'X-Session-Token': sessionToken } : {},
    }),
  logEvent: (body) => api.post('/proctoring/event', body),
  answerTiming: (body) => api.post('/proctoring/answer-timing', body),
  biometrics: (body) => api.post('/proctoring/biometrics', body),
  getReport: (quizId) => api.get(`/proctoring/report/${quizId}`),
  getSnapshots: (quizId, participantId) => api.get(`/proctoring/snapshots/${quizId}/${participantId}`),
  lockSession: (token) => api.post(`/proctoring/lock/${token}`),
  unlockSession: (token) => api.post(`/proctoring/unlock/${token}`),
  getPlatformRules: () => api.get('/proctoring/admin/rules'),
  updatePlatformRule: (ruleId, body) => api.put(`/proctoring/admin/rules/${ruleId}`, body),
  getTenantPolicy: (tenantId) => api.get(`/proctoring/admin/tenant-policy/${tenantId}`),
  updateTenantPolicy: (tenantId, body) => api.put(`/proctoring/admin/tenant-policy/${tenantId}`, body),
}

export default api
