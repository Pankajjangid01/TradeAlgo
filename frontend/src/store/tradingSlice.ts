import { createSlice, PayloadAction } from '@reduxjs/toolkit';

export interface Position {
  id: string;
  instrument: string;
  symbol: string;
  side: 'long' | 'short';
  quantity: number;
  averagePrice: number;
  currentPrice: number;
  unrealizedPnl: number;
  realizedPnl: number;
  stopPrice?: number;
  targetPrice?: number;
  trailingStop?: number;
  isOpen: boolean;
  openedAt: string;
  closedAt?: string;
}

export interface Order {
  id: string;
  internalId: string;
  brokerOrderId?: string;
  instrument: string;
  symbol: string;
  side: 'buy' | 'sell';
  orderType: 'market' | 'limit' | 'sl' | 'sl_m';
  quantity: number;
  filledQuantity: number;
  price?: number;
  triggerPrice?: number;
  averagePrice?: number;
  status: 'created' | 'validated' | 'submitted' | 'acknowledged' | 'partially_filled' | 'filled' | 'rejected' | 'cancel_pending' | 'cancelled' | 'expired' | 'unknown';
  productType: string;
  validity: string;
  tag?: string;
  errorMessage?: string;
  createdAt: string;
  updatedAt: string;
  submittedAt?: string;
  acknowledgedAt?: string;
  filledAt?: string;
  cancelledAt?: string;
}

export interface Funds {
  availableCash: number;
  availableMargin: number;
  usedMargin: number;
  totalCollateral?: number;
  unsettledAmount?: number;
  lastUpdated: string;
}

export interface RiskMetrics {
  dailyPnl: number;
  maxDailyLoss: number;
  dailyLossLimit: number;
  openPositions: number;
  maxPositions: number;
  consecutiveLosses: number;
  maxConsecutiveLosses: number;
  killSwitchActive: boolean;
  totalExposure: number;
  maxExposure: number;
}

interface TradingState {
  positions: Position[];
  orders: Order[];
  funds: Funds | null;
  riskMetrics: RiskMetrics;
  tradingMode: 'paper' | 'live';
  isTradingEnabled: boolean;
  selectedBroker: 'angelone' | 'flattrade';
  loading: boolean;
  error: string | null;
}

const initialState: TradingState = {
  positions: [],
  orders: [],
  funds: null,
  riskMetrics: {
    dailyPnl: 0,
    maxDailyLoss: 0,
    dailyLossLimit: 5000,
    openPositions: 0,
    maxPositions: 1,
    consecutiveLosses: 0,
    maxConsecutiveLosses: 3,
    killSwitchActive: false,
    totalExposure: 0,
    maxExposure: 100000,
  },
  tradingMode: 'paper',
  isTradingEnabled: false,
  selectedBroker: 'angelone',
  loading: false,
  error: null,
};

const tradingSlice = createSlice({
  name: 'trading',
  initialState,
  reducers: {
    setPositions(state, action: PayloadAction<Position[]>) {
      state.positions = action.payload;
      state.riskMetrics.openPositions = action.payload.filter(p => p.isOpen).length;
    },
    updatePosition(state, action: PayloadAction<Partial<Position> & { id: string }>) {
      const index = state.positions.findIndex(p => p.id === action.payload.id);
      if (index !== -1) {
        state.positions[index] = { ...state.positions[index], ...action.payload };
      }
    },
    addPosition(state, action: PayloadAction<Position>) {
      state.positions.unshift(action.payload);
      state.riskMetrics.openPositions = state.positions.filter(p => p.isOpen).length;
    },
    removePosition(state, action: PayloadAction<string>) {
      state.positions = state.positions.filter(p => p.id !== action.payload);
      state.riskMetrics.openPositions = state.positions.filter(p => p.isOpen).length;
    },
    setOrders(state, action: PayloadAction<Order[]>) {
      state.orders = action.payload;
    },
    addOrder(state, action: PayloadAction<Order>) {
      state.orders.unshift(action.payload);
    },
    updateOrder(state, action: PayloadAction<Partial<Order> & { id: string }>) {
      const index = state.orders.findIndex(o => o.id === action.payload.id);
      if (index !== -1) {
        state.orders[index] = { ...state.orders[index], ...action.payload };
      }
    },
    setFunds(state, action: PayloadAction<Funds>) {
      state.funds = action.payload;
    },
    setRiskMetrics(state, action: PayloadAction<Partial<RiskMetrics>>) {
      state.riskMetrics = { ...state.riskMetrics, ...action.payload };
    },
    setTradingMode(state, action: PayloadAction<'paper' | 'live'>) {
      state.tradingMode = action.payload;
    },
    setTradingEnabled(state, action: PayloadAction<boolean>) {
      state.isTradingEnabled = action.payload;
    },
    setSelectedBroker(state, action: PayloadAction<'angelone' | 'flattrade'>) {
      state.selectedBroker = action.payload;
    },
    setLoading(state, action: PayloadAction<boolean>) {
      state.loading = action.payload;
    },
    setError(state, action: PayloadAction<string | null>) {
      state.error = action.payload;
    },
    toggleKillSwitch(state) {
      state.riskMetrics.killSwitchActive = !state.riskMetrics.killSwitchActive;
    },
  },
});

export const {
  setPositions,
  updatePosition,
  addPosition,
  removePosition,
  setOrders,
  addOrder,
  updateOrder,
  setFunds,
  setRiskMetrics,
  setTradingMode,
  setTradingEnabled,
  setSelectedBroker,
  setLoading,
  setError,
  toggleKillSwitch,
} = tradingSlice.actions;

export default tradingSlice.reducer;