import { createSlice, PayloadAction } from '@reduxjs/toolkit';

interface UIState {
  sidebarOpen: boolean;
  activeTab: string;
  theme: 'dark' | 'light';
  notifications: Array<{
    id: string;
    type: 'success' | 'error' | 'warning' | 'info';
    message: string;
    timestamp: string;
  }>;
  modals: Record<string, boolean>;
  loadingStates: Record<string, boolean>;
  selectedDateRange: { start: string; end: string } | null;
}

const initialState: UIState = {
  sidebarOpen: true,
  activeTab: 'dashboard',
  theme: 'dark',
  notifications: [],
  modals: {},
  loadingStates: {},
  selectedDateRange: null,
};

const uiSlice = createSlice({
  name: 'ui',
  initialState,
  reducers: {
    toggleSidebar(state) {
      state.sidebarOpen = !state.sidebarOpen;
    },
    setSidebarOpen(state, action: PayloadAction<boolean>) {
      state.sidebarOpen = action.payload;
    },
    setActiveTab(state, action: PayloadAction<string>) {
      state.activeTab = action.payload;
    },
    setTheme(state, action: PayloadAction<'dark' | 'light'>) {
      state.theme = action.payload;
    },
    addNotification(state, action: PayloadAction<{ type: UIState['notifications'][0]['type']; message: string }>) {
      const notification = {
        id: Date.now().toString(),
        ...action.payload,
        timestamp: new Date().toISOString(),
      };
      state.notifications.unshift(notification);
      if (state.notifications.length > 20) {
        state.notifications = state.notifications.slice(0, 20);
      }
    },
    removeNotification(state, action: PayloadAction<string>) {
      state.notifications = state.notifications.filter(n => n.id !== action.payload);
    },
    clearNotifications(state) {
      state.notifications = [];
    },
    openModal(state, action: PayloadAction<string>) {
      state.modals[action.payload] = true;
    },
    closeModal(state, action: PayloadAction<string>) {
      state.modals[action.payload] = false;
    },
    setLoadingState(state, action: PayloadAction<{ key: string; loading: boolean }>) {
      state.loadingStates[action.payload.key] = action.payload.loading;
    },
    setDateRange(state, action: PayloadAction<{ start: string; end: string } | null>) {
      state.selectedDateRange = action.payload;
    },
  },
});

export const {
  toggleSidebar,
  setSidebarOpen,
  setActiveTab,
  setTheme,
  addNotification,
  removeNotification,
  clearNotifications,
  openModal,
  closeModal,
  setLoadingState,
  setDateRange,
} = uiSlice.actions;

export default uiSlice.reducer;