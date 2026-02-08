import { createSlice } from '@reduxjs/toolkit'

const initialState = {
  sessionId: null,
  sessionToken: null,
  quizTitle: '',
  status: 'created',
  currentQuestionIndex: -1,
  currentQuestion: null,
  participantCount: 0,
  hasAnswered: false,
  results: null,
}

export const sessionSlice = createSlice({
  name: 'session',
  initialState,
  reducers: {
    setSession: (state, action) => {
      state.sessionId = action.payload.session_id
      state.sessionToken = action.payload.session_token
      state.quizTitle = action.payload.quiz_title
      state.status = action.payload.status
    },
    updateSessionStatus: (state, action) => {
      state.status = action.payload.status
      state.currentQuestionIndex = action.payload.current_question_index
      state.currentQuestion = action.payload.current_question
      state.participantCount = action.payload.participant_count
      state.hasAnswered = false
    },
    markAnswered: (state) => {
      state.hasAnswered = true
    },
    setResults: (state, action) => {
      state.results = action.payload
    },
    clearSession: (state) => {
      return initialState
    },
  },
})

export const { 
  setSession, 
  updateSessionStatus, 
  markAnswered, 
  setResults, 
  clearSession 
} = sessionSlice.actions

export default sessionSlice.reducer
