import torch
import torch.nn as nn
import numpy as np
from sklearn.preprocessing import MinMaxScaler
import logging
import os
import pickle
from pathlib import Path

logger = logging.getLogger(__name__)
MODELS_DIR = Path(__file__).parent / "models"
MODELS_DIR.mkdir(exist_ok=True)


class LSTMPredictor(nn.Module):
    def __init__(self, input_size=5, hidden_size=64, num_layers=2, dropout=0.2):
        super().__init__()
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True, dropout=dropout)
        self.fc = nn.Sequential(nn.Linear(hidden_size, 32), nn.ReLU(), nn.Linear(32, 1))

    def forward(self, x):
        h0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size)
        c0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size)
        out, _ = self.lstm(x, (h0, c0))
        return self.fc(out[:, -1, :])


class CryptoLSTM:
    def __init__(self, symbol="BTC/USDT", lookback=30, epochs=50, lr=0.001):
        self.symbol = symbol
        self.lookback = lookback
        self.epochs = epochs
        self.lr = lr
        self.model = LSTMPredictor()
        self.scaler = MinMaxScaler()
        self.price_scaler = MinMaxScaler()
        self.trained = False
        self.last_loss = None
        # Try to load saved model
        self._load()

    def _model_path(self):
        safe = self.symbol.replace("/", "_")
        return MODELS_DIR / f"lstm_{safe}.pt"

    def _scaler_path(self):
        safe = self.symbol.replace("/", "_")
        return MODELS_DIR / f"scalers_{safe}.pkl"

    def _save(self):
        try:
            torch.save(self.model.state_dict(), self._model_path())
            with open(self._scaler_path(), 'wb') as f:
                pickle.dump({"scaler": self.scaler, "price_scaler": self.price_scaler}, f)
            logger.info(f"LSTM model saved for {self.symbol}")
        except Exception as e:
            logger.error(f"LSTM save error: {e}")

    def _load(self):
        try:
            mp, sp = self._model_path(), self._scaler_path()
            if mp.exists() and sp.exists():
                self.model.load_state_dict(torch.load(mp, weights_only=True))
                with open(sp, 'rb') as f:
                    d = pickle.load(f)
                self.scaler = d["scaler"]
                self.price_scaler = d["price_scaler"]
                self.trained = True
                logger.info(f"LSTM model loaded for {self.symbol}")
        except Exception as e:
            logger.error(f"LSTM load error: {e}")

    def prepare_data(self, df):
        features = df[['open', 'high', 'low', 'close', 'volume']].values
        prices = df[['close']].values
        scaled_features = self.scaler.fit_transform(features)
        scaled_prices = self.price_scaler.fit_transform(prices)
        X, y = [], []
        for i in range(self.lookback, len(scaled_features)):
            X.append(scaled_features[i - self.lookback:i])
            y.append(scaled_prices[i, 0])
        return np.array(X), np.array(y)

    def train(self, df):
        if df is None or len(df) < self.lookback + 20:
            return False
        try:
            X, y = self.prepare_data(df)
            if len(X) < 10:
                return False
            X_t = torch.FloatTensor(X)
            y_t = torch.FloatTensor(y).unsqueeze(1)
            split = int(len(X) * 0.8)
            X_train, y_train = X_t[:split], y_t[:split]
            optimizer = torch.optim.Adam(self.model.parameters(), lr=self.lr)
            criterion = nn.MSELoss()
            self.model.train()
            for epoch in range(self.epochs):
                optimizer.zero_grad()
                output = self.model(X_train)
                loss = criterion(output, y_train)
                loss.backward()
                optimizer.step()
            self.trained = True
            self.last_loss = loss.item()
            self._save()
            logger.info(f"LSTM trained for {self.symbol}. Loss: {self.last_loss:.6f}")
            return True
        except Exception as e:
            logger.error(f"LSTM training error: {e}")
            return False

    def predict(self, df):
        if not self.trained or df is None or len(df) < self.lookback:
            return {"signal": "HOLD", "confidence": 0, "predicted_direction": "NEUTRAL"}
        try:
            self.model.eval()
            features = df[['open', 'high', 'low', 'close', 'volume']].values
            scaled = self.scaler.transform(features)
            X = torch.FloatTensor(scaled[-self.lookback:]).unsqueeze(0)
            with torch.no_grad():
                pred_scaled = self.model(X).item()
            pred_price = self.price_scaler.inverse_transform([[pred_scaled]])[0][0]
            current_price = df['close'].iloc[-1]
            pct_change = (pred_price - current_price) / current_price * 100
            if pct_change > 0.15:
                signal, direction = "BUY", "UP"
            elif pct_change < -0.15:
                signal, direction = "SELL", "DOWN"
            else:
                signal, direction = "HOLD", "NEUTRAL"
            return {
                "signal": signal, "confidence": round(min(abs(pct_change) * 20, 100), 1),
                "predicted_direction": direction, "predicted_change_pct": round(pct_change, 4),
                "predicted_price": round(pred_price, 2), "current_price": round(current_price, 2),
            }
        except Exception as e:
            logger.error(f"LSTM prediction error: {e}")
            return {"signal": "HOLD", "confidence": 0, "predicted_direction": "NEUTRAL"}


lstm_models = {}

def get_lstm(symbol="BTC/USDT"):
    if symbol not in lstm_models:
        lstm_models[symbol] = CryptoLSTM(symbol=symbol, lookback=30, epochs=30)
    return lstm_models[symbol]
