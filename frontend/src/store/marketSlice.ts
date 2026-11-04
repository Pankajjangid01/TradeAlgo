import { createSlice, PayloadAction } from '@reduxjs/toolkit';

export interface TickData {
  instrument_token: string;
  timestamp: string;
  ltp: number;
  volume: number;
  oi?: number;
  bid?: number;
  ask?: number;
  bid_qty?: number;
  ask_qty?: number;
}

export interface CandleData {
  instrument_token: string;
  timeframe: string;
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  oi?: number;
  vwap?: number;
}

export interface Instrument {
  symbol: string;
  name: string;
  token: string;
  exchange: string;
  lot_size: number;
  tick_size: number;
  expiry?: string;
  strike?: number;
  option_type?: string;
  underlying?: string;
}

interface MarketState {
  ticks: Record<string, TickData>;
  candles: Record<string, CandleData[]>;
  instruments: Instrument[];
  selectedInstrument: string | null;
  selectedTimeframe: string;
  isConnected: boolean;
  connectionError: string | null;
  lastUpdate: string | null;
}

const initialState: MarketState = {
  ticks: {},
  candles: {},
  instruments: [],
  selectedInstrument: 'NIFTY',
  selectedTimeframe: '5m',
  isConnected: false,
  connectionError: null,
  lastUpdate: null,
};

const marketSlice = createSlice({
  name: 'market',
  initialState,
  reducers: {
    setTicks(state, action: PayloadAction<TickData[]>) {
      action.payload.forEach(tick => {
        state.ticks[tick.instrument_token] = tick;
      });
      state.lastUpdate = new Date().toISOString();
    },
    setCandles(state, action: PayloadAction<{ instrument: string; timeframe: string; candles: CandleData[] }>) {
      const key = `${action.payload.instrument}_${action.payload.timeframe}`;
      state.candles[key] = action.payload.candles;
    },
    setInstruments(state, action: PayloadAction<Instrument[]>) {
      state.instruments = action.payload;
    },
    setSelectedInstrument(state, action: PayloadAction<string>) {
      state.selectedInstrument = action.payload;
    },
    setSelectedTimeframe(state, action: PayloadAction<string>) {
      state.selectedTimeframe = action.payload;
    },
    setConnectionStatus(state, action: PayloadAction<{ connected: boolean; error?: string }>) {
      state.isConnected = action.payload.connected;
      state.connectionError = action.payload.error || null;
    },
    clearTicks(state) {
      state.ticks = {};
    },
  },
});

export const {
  setTicks,
  setCandles,
  setInstruments,
  setSelectedInstrument,
  setSelectedTimeframe,
  setConnectionStatus,
  clearTicks,
} = marketSlice.actions;

export default marketSlice.reducer;