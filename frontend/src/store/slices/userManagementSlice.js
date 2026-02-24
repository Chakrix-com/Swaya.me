import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import api from '../../services/api';

// Async thunks
export const fetchUsers = createAsyncThunk(
  'userManagement/fetchUsers',
  async (params = {}) => {
    const response = await api.get('/users', { params });
    return response.data;
  }
);

export const fetchUser = createAsyncThunk(
  'userManagement/fetchUser',
  async (userId) => {
    const response = await api.get(`/users/${userId}`);
    return response.data;
  }
);

export const createUser = createAsyncThunk(
  'userManagement/createUser',
  async (userData) => {
    const response = await api.post('/users', userData);
    return response.data;
  }
);

export const updateUser = createAsyncThunk(
  'userManagement/updateUser',
  async ({ userId, updates }) => {
    const response = await api.patch(`/users/${userId}`, updates);
    return response.data;
  }
);

export const deleteUser = createAsyncThunk(
  'userManagement/deleteUser',
  async (userId) => {
    await api.delete(`/users/${userId}`);
    return userId;
  }
);

export const fetchUserStats = createAsyncThunk(
  'userManagement/fetchUserStats',
  async (userId) => {
    const response = await api.get(`/users/${userId}/stats`);
    return response.data;
  }
);

export const fetchUserActivities = createAsyncThunk(
  'userManagement/fetchUserActivities',
  async ({ userId, page = 1, perPage = 50 }) => {
    const response = await api.get(`/users/${userId}/activities`, {
      params: { page, per_page: perPage }
    });
    return response.data;
  }
);

export const updatePassword = createAsyncThunk(
  'userManagement/updatePassword',
  async ({ userId, currentPassword, newPassword }) => {
    const response = await api.post(`/users/${userId}/password`, {
      current_password: currentPassword,
      new_password: newPassword
    });
    return response.data;
  }
);

const userManagementSlice = createSlice({
  name: 'userManagement',
  initialState: {
    users: [],
    currentUser: null,
    userStats: null,
    activities: [],
    total: 0,
    page: 1,
    perPage: 20,
    pages: 0,
    loading: false,
    error: null
  },
  reducers: {
    clearError: (state) => {
      state.error = null;
    },
    clearCurrentUser: (state) => {
      state.currentUser = null;
      state.userStats = null;
      state.activities = [];
    }
  },
  extraReducers: (builder) => {
    builder
      // Fetch users
      .addCase(fetchUsers.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchUsers.fulfilled, (state, action) => {
        state.loading = false;
        state.users = action.payload.users;
        state.total = action.payload.total;
        state.page = action.payload.page;
        state.perPage = action.payload.per_page;
        state.pages = action.payload.pages;
      })
      .addCase(fetchUsers.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message;
      })
      
      // Fetch user
      .addCase(fetchUser.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchUser.fulfilled, (state, action) => {
        state.loading = false;
        state.currentUser = action.payload;
      })
      .addCase(fetchUser.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message;
      })
      
      // Create user
      .addCase(createUser.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(createUser.fulfilled, (state, action) => {
        state.loading = false;
        state.users.unshift(action.payload);
        state.total += 1;
      })
      .addCase(createUser.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message;
      })
      
      // Update user
      .addCase(updateUser.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(updateUser.fulfilled, (state, action) => {
        state.loading = false;
        const index = state.users.findIndex(u => u.id === action.payload.id);
        if (index !== -1) {
          state.users[index] = action.payload;
        }
        if (state.currentUser?.id === action.payload.id) {
          state.currentUser = action.payload;
        }
      })
      .addCase(updateUser.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message;
      })
      
      // Delete user
      .addCase(deleteUser.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(deleteUser.fulfilled, (state, action) => {
        state.loading = false;
        state.users = state.users.filter(u => u.id !== action.payload);
        state.total -= 1;
      })
      .addCase(deleteUser.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message;
      })
      
      // Fetch user stats
      .addCase(fetchUserStats.fulfilled, (state, action) => {
        state.userStats = action.payload;
      })
      
      // Fetch activities
      .addCase(fetchUserActivities.fulfilled, (state, action) => {
        state.activities = action.payload.activities;
      });
  }
});

export const { clearError, clearCurrentUser } = userManagementSlice.actions;
export default userManagementSlice.reducer;
