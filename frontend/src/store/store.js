import { combineReducers, configureStore } from '@reduxjs/toolkit'
import authReducer, { logout } from './authSlice'
import quizReducer from './quizSlice'
import sessionReducer from './sessionSlice'
import userManagementReducer from './slices/userManagementSlice'
import tenantManagementReducer from './slices/tenantManagementSlice'
import themeReducer from './themeSlice'

const appReducer = combineReducers({
  auth: authReducer,
  quiz: quizReducer,
  session: sessionReducer,
  userManagement: userManagementReducer,
  tenantManagement: tenantManagementReducer,
  theme: themeReducer,
})

// Wipe tenant-scoped state on logout so a subsequent login (in the same tab,
// no full page reload) can't inherit the previous account's quizzes, folders,
// or sessions. `theme` (a personal UI preference) and `auth` are preserved
// as-is: `auth` must go through appReducer normally so authSlice's own
// `logout` reducer clears user/isAuthenticated in place — resetting it to
// authSlice's raw initialState here would also reset `loading: true`, which
// nothing re-clears after the one-time startup check in App.jsx, leaving
// the app stuck on its loading spinner forever.
const rootReducer = (state, action) => {
  if (action.type === logout.type) {
    state = { theme: state?.theme, auth: state?.auth }
  }
  return appReducer(state, action)
}

export const store = configureStore({
  reducer: rootReducer,
})
