import { createSlice } from '@reduxjs/toolkit'

const initialState = {
  user: null,
  isAuthenticated: false,
  loading: true,  // true while startup /auth/me check runs
  error: null,
}

export const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    loginStart: (state) => {
      state.loading = true
      state.error = null
    },
    loginSuccess: (state, action) => {
      state.loading = false
      state.isAuthenticated = true
      state.user = action.payload.user
      // JWT is stored in HttpOnly cookie by the server — not in localStorage
    },
    loginFailure: (state, action) => {
      state.loading = false
      state.error = action.payload
    },
    logout: (state) => {
      state.user = null
      state.isAuthenticated = false
    },
    refreshUser: (state, action) => {
      state.user = action.payload
    },
    initAuth: (state, action) => {
      state.loading = false
      state.user = action.payload
      state.isAuthenticated = !!action.payload
    },
  },
})

export const { loginStart, loginSuccess, loginFailure, logout, refreshUser, initAuth } = authSlice.actions
export default authSlice.reducer
