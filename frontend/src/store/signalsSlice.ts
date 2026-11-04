import { createSlice, PayloadAction } from '@reduxjs/toolkit';

export interface Signal {
  id: string;
  instrument: string;
  strategy: 'orb' | 'vwap_pullback' | 'sr_breakout';
  direction: 'bullish' | 'bearish';
  status: 'watchlist' | 'setup_forming' | 'wait_for_confirmation' | 'approved' | 'rejected' | 'order_pending' | 'position_open' | 'exit_pending' | 'closed' | 'error' | 'halted';
  entryPrice: number;
  stopPrice: number;
  targetPrice: number;
  riskPerShare: number;
  rewardPerShare: number;
  rrRatio: number;
  confidence: number;
  regime: string;
  indicators: Record<string, number>;
  structure: Record<string, any>;
  mlPrediction: Record<string, any>;
  rejectionReason?: string;
  createdAt: string;
  updatedAt: string;
  approvedAt?: string;
  executedAt?: string;
  closedAt?: string;
}

interface SignalsState {
  signals: Signal[];
  activeSignal: Signal | null;
  history: Signal[];
  filters: {
    strategy: string[];
    direction: string[];
    status: string[];
  };
  loading: boolean;
  error: string | null;
}

const initialState: SignalsState = {
  signals: [],
  activeSignal: null,
  history: [],
  filters: {
    strategy: [],
    direction: [],
    status: [],
  },
  loading: false,
  error: null,
};

const signalsSlice = createSlice({
  name: 'signals',
  initialState,
  reducers: {
    setSignals(state, action: PayloadAction<Signal[]>) {
      state.signals = action.payload;
    },
    addSignal(state, action: PayloadAction<Signal>) {
      state.signals.unshift(action.payload);
      // Keep only last 100
      if (state.signals.length > 100) {
        state.signals = state.signals.slice(0, 100);
      }
    },
    updateSignal(state, action: PayloadAction<Partial<Signal> & { id: string }>) {
      const index = state.signals.findIndex(s => s.id === action.payload.id);
      if (index !== -1) {
        state.signals[index] = { ...state.signals[index], ...action.payload };
      }
      if (state.activeSignal?.id === action.payload.id) {
        state.activeSignal = { ...state.activeSignal, ...action.payload };
      }
    },
    setActiveSignal(state, action: PayloadAction<Signal | null>) {
      state.activeSignal = action.payload;
    },
    addToHistory(state, action: PayloadAction<Signal>) {
      state.history.unshift(action.payload);
      if (state.history.length > 500) {
        state.history = state.history.slice(0, 500);
      }
    },
    setFilters(state, action: PayloadAction<Partial<SignalsState['filters']>>) {
      state.filters = { ...state.filters, ...action.payload };
    },
    setLoading(state, action: PayloadAction<boolean>) {
      state.loading = action.payload;
    },
    setError(state, action: PayloadAction<string | null>) {
      state.error = action.payload;
    },
    clearSignals(state) {
      state.signals = [];
      state.activeSignal = null;
    },
  },
});

export const {
  setSignals,
  addSignal,
  updateSignal,
  setActiveSignal,
  addToHistory,
  setFilters,
  setLoading,
  setError,
  clearSignals,
} = signalsSlice.actions;

export default signalsSlice.reducer;