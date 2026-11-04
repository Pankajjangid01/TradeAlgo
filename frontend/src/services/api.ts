import axios, { AxiosInstance, InternalAxiosRequestConfig } from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || '/api/v1';

class ApiService {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    this.client.interceptors.request.use(
      (config: InternalAxiosRequestConfig) => {
        // Add auth token if available
        const token = localStorage.getItem('auth_token');
        if (token && config.headers) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          // Handle unauthorized
          localStorage.removeItem('auth_token');
          window.location.href = '/login';
        }
        return Promise.reject(error);
      }
    );
  }

  setAuthToken(token: string | null) {
    if (token) {
      this.client.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    } else {
      delete this.client.defaults.headers.common['Authorization'];
    }
  }

  // Market Data
  async getLTP(symbols: string, exchange: string = 'NSE') {
    return this.client.get('/market/ltp', { params: { symbols, exchange } });
  }

  async getQuote(symbols: string, exchange: string = 'NSE') {
    return this.client.get('/market/quote', { params: { symbols, exchange } });
  }

  async getHistorical(symbolToken: string, interval: string, fromDate: string, toDate: string, exchange: string = 'NSE') {
    return this.client.get('/market/historical', { params: { symbol_token: symbolToken, interval, from_date: fromDate, to_date: toDate, exchange } });
  }

  async searchInstruments(query: string, exchange: string = 'NSE') {
    return this.client.get('/market/instruments', { params: { q: query, exchange } });
  }

  async getOptionChain(underlying: string, expiry?: string) {
    return this.client.get('/market/option-chain', { params: { underlying, expiry } });
  }

  async setDataProvider(provider: string) {
    return this.client.post('/market/provider', { provider });
  }

  // Account
  async getFunds() {
    return this.client.get('/account/funds');
  }

  async getPositions() {
    return this.client.get('/account/positions');
  }

  async getHoldings() {
    return this.client.get('/account/holdings');
  }

  async getOrders() {
    return this.client.get('/account/orders');
  }

  // Signals
  async analyzeMarket(symbol: string, timeframe: string = '5m', lookbackBars: number = 100) {
    return this.client.post('/signals/analyze', { symbol, timeframe, lookback_bars: lookbackBars });
  }

  async getActiveSignals() {
    return this.client.get('/signals/active');
  }

  // Orders
  async placeOrder(order: any) {
    return this.client.post('/orders/place', order);
  }

  async modifyOrder(orderId: string, price?: number, quantity?: number, triggerPrice?: number) {
    return this.client.post(`/orders/${orderId}/modify`, { price, quantity, trigger_price: triggerPrice });
  }

  async cancelOrder(orderId: string) {
    return this.client.post(`/orders/${orderId}/cancel`);
  }

  // Risk
  async checkRisk(params: any) {
    return this.client.post('/risk/check', params);
  }

  async calculatePositionSize(params: any) {
    return this.client.post('/risk/position-size', params);
  }

  // Options
  async selectOption(params: any) {
    return this.client.post('/options/select', params);
  }

  // Backtesting
  async runBacktest(params: any) {
    return this.client.post('/backtest/run', params);
  }

  async getBacktestResults(runId: string) {
    return this.client.get(`/backtest/${runId}`);
  }

  // Health
  async healthCheck() {
    return this.client.get('/health');
  }

  async systemStatus() {
    return this.client.get('/status');
  }
}

export const api = new ApiService();