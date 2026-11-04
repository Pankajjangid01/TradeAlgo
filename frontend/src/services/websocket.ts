import { io, Socket } from 'socket.io-client';

type MarketDataCallback = (data: any) => void;
type ConnectionCallback = (connected: boolean) => void;

class WebSocketService {
  private socket: Socket | null = null;
  private marketDataCallbacks: Map<string, MarketDataCallback[]> = new Map();
  private connectionCallbacks: ConnectionCallback[] = [];
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 10;
  private reconnectDelay = 1000;

  connect(url: string = '') {
    if (this.socket?.connected) {
      return;
    }

    this.socket = io(url || window.location.origin, {
      path: '/ws',
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionAttempts: this.maxReconnectAttempts,
      reconnectionDelay: this.reconnectDelay,
      autoConnect: true,
    });

    this.socket.on('connect', () => {
      console.log('WebSocket connected');
      this.reconnectAttempts = 0;
      this.notifyConnectionCallbacks(true);
    });

    this.socket.on('disconnect', (reason) => {
      console.log('WebSocket disconnected:', reason);
      this.notifyConnectionCallbacks(false);
    });

    this.socket.on('connect_error', (error) => {
      console.error('WebSocket connection error:', error);
      this.reconnectAttempts++;
    });

    this.socket.on('market_data', (data) => {
      this.notifyMarketDataCallbacks('market_data', data);
    });

    this.socket.on('tick', (data) => {
      this.notifyMarketDataCallbacks('tick', data);
    });

    this.socket.on('candle', (data) => {
      this.notifyMarketDataCallbacks('candle', data);
    });

    this.socket.on('signal', (data) => {
      this.notifyMarketDataCallbacks('signal', data);
    });

    this.socket.on('order_update', (data) => {
      this.notifyMarketDataCallbacks('order_update', data);
    });

    this.socket.on('position_update', (data) => {
      this.notifyMarketDataCallbacks('position_update', data);
    });

    this.socket.on('risk_alert', (data) => {
      this.notifyMarketDataCallbacks('risk_alert', data);
    });
  }

  disconnect() {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
    }
  }

  subscribe(tokens: string[]) {
    if (this.socket?.connected) {
      this.socket.emit('subscribe', { tokens });
    }
  }

  unsubscribe(tokens: string[]) {
    if (this.socket?.connected) {
      this.socket.emit('unsubscribe', { tokens });
    }
  }

  onMarketData(event: string, callback: MarketDataCallback) {
    if (!this.marketDataCallbacks.has(event)) {
      this.marketDataCallbacks.set(event, []);
    }
    this.marketDataCallbacks.get(event)!.push(callback);

    // Return unsubscribe function
    return () => {
      const callbacks = this.marketDataCallbacks.get(event);
      if (callbacks) {
        const index = callbacks.indexOf(callback);
        if (index !== -1) {
          callbacks.splice(index, 1);
        }
      }
    };
  }

  onConnectionChange(callback: ConnectionCallback) {
    this.connectionCallbacks.push(callback);
    return () => {
      const index = this.connectionCallbacks.indexOf(callback);
      if (index !== -1) {
        this.connectionCallbacks.splice(index, 1);
      }
    };
  }

  private notifyMarketDataCallbacks(event: string, data: any) {
    const callbacks = this.marketDataCallbacks.get(event);
    if (callbacks) {
      callbacks.forEach(cb => {
        try {
          cb(data);
        } catch (error) {
          console.error(`Error in ${event} callback:`, error);
        }
      });
    }
  }

  private notifyConnectionCallbacks(connected: boolean) {
    this.connectionCallbacks.forEach(cb => {
      try {
        cb(connected);
      } catch (error) {
        console.error('Error in connection callback:', error);
      }
    });
  }

  isConnected(): boolean {
    return this.socket?.connected ?? false;
  }
}

export const wsService = new WebSocketService();