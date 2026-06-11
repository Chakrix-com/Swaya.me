import { configureStore } from '@reduxjs/toolkit'
import authReducer from './authSlice'
import quizReducer from './quizSlice'
import sessionReducer from './sessionSlice'
import userManagementReducer from './slices/userManagementSlice'
import tenantManagementReducer from './slices/tenantManagementSlice'
import themeReducer from './themeSlice'

export const store = configureStore({
  reducer: {
    auth: authReducer,
    quiz: quizReducer,
    session: sessionReducer,
    userManagement: userManagementReducer,
    tenantManagement: tenantManagementReducer,
    theme: themeReducer,
  },
})
