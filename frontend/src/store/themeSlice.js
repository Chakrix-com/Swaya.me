import { createSlice } from '@reduxjs/toolkit'
import { themes, DEFAULT_THEME_ID } from '../themes/themes'

const STORAGE_KEY = 'uiThemeId'

const stored = localStorage.getItem(STORAGE_KEY)

const themeSlice = createSlice({
  name: 'theme',
  initialState: {
    themeId: themes[stored] ? stored : DEFAULT_THEME_ID,
  },
  reducers: {
    setTheme: (state, action) => {
      if (!themes[action.payload]) return
      state.themeId = action.payload
      localStorage.setItem(STORAGE_KEY, action.payload)
    },
  },
})

export const { setTheme } = themeSlice.actions
export default themeSlice.reducer
