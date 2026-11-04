import { configureStore } from '@reduxjs/toolkit';
import marketReducer from './marketSlice';
import signalsReducer from './signalsSlice';
import tradingReducer from './tradingSlice';
import uiReducer from './uiSlice';

export const store = configureStore({
  reducer: {
    market: marketReducer,
    signals: signalsReducer,
    trading: tradingReducer,
    ui: uiReducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        ignoredActions: ['market/setTicks', 'market/setCandles'],
        ignoredPaths: ['market.ticks', 'market.candles'],
      },
    }),
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;