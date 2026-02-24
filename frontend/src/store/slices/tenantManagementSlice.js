import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import api from '../../services/api';

// Async thunks
export const fetchTenants = createAsyncThunk(
  'tenantManagement/fetchTenants',
  async (params = {}) => {
    const response = await api.get('/tenants', { params });
    return response.data;
  }
);

export const fetchTenant = createAsyncThunk(
  'tenantManagement/fetchTenant',
  async (tenantId) => {
    const response = await api.get(`/tenants/${tenantId}`);
    return response.data;
  }
);

export const updateTenant = createAsyncThunk(
  'tenantManagement/updateTenant',
  async ({ tenantId, updates }) => {
    const response = await api.patch(`/tenants/${tenantId}`, updates);
    return response.data;
  }
);

const tenantManagementSlice = createSlice({
  name: 'tenantManagement',
  initialState: {
    tenants: [],
    currentTenant: null,
    total: 0,
    page: 1,
    perPage: 20,
    loading: false,
    error: null
  },
  reducers: {
    clearError: (state) => {
      state.error = null;
    },
    clearCurrentTenant: (state) => {
      state.currentTenant = null;
    }
  },
  extraReducers: (builder) => {
    builder
      // Fetch tenants
      .addCase(fetchTenants.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchTenants.fulfilled, (state, action) => {
        state.loading = false;
        state.tenants = action.payload.tenants;
        state.total = action.payload.total;
        state.page = action.payload.page;
        state.perPage = action.payload.per_page;
      })
      .addCase(fetchTenants.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message;
      })
      
      // Fetch tenant
      .addCase(fetchTenant.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchTenant.fulfilled, (state, action) => {
        state.loading = false;
        state.currentTenant = action.payload;
      })
      .addCase(fetchTenant.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message;
      })
      
      // Update tenant
      .addCase(updateTenant.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(updateTenant.fulfilled, (state, action) => {
        state.loading = false;
        const index = state.tenants.findIndex(t => t.id === action.payload.id);
        if (index !== -1) {
          state.tenants[index] = action.payload;
        }
        if (state.currentTenant?.id === action.payload.id) {
          state.currentTenant = action.payload;
        }
      })
      .addCase(updateTenant.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message;
      });
  }
});

export const { clearError, clearCurrentTenant } = tenantManagementSlice.actions;
export default tenantManagementSlice.reducer;
