import { createSlice } from '@reduxjs/toolkit'

const initialState = {
  quizzes: [],
  currentQuiz: null,
  questions: [],
  loading: false,
  error: null,
}

export const quizSlice = createSlice({
  name: 'quiz',
  initialState,
  reducers: {
    setQuizzes: (state, action) => {
      state.quizzes = action.payload
    },
    setCurrentQuiz: (state, action) => {
      state.currentQuiz = action.payload
      state.questions = action.payload?.questions || []
    },
    addQuestion: (state, action) => {
      state.questions.push(action.payload)
    },
    updateQuestion: (state, action) => {
      const index = state.questions.findIndex(q => q.id === action.payload.id)
      if (index !== -1) {
        state.questions[index] = action.payload
      }
    },
    deleteQuestion: (state, action) => {
      state.questions = state.questions.filter(q => q.id !== action.payload)
    },
    setLoading: (state, action) => {
      state.loading = action.payload
    },
    setError: (state, action) => {
      state.error = action.payload
    },
  },
})

export const { 
  setQuizzes, 
  setCurrentQuiz, 
  addQuestion, 
  updateQuestion, 
  deleteQuestion,
  setLoading,
  setError 
} = quizSlice.actions

export default quizSlice.reducer
