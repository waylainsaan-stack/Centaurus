import torch
import torch.nn as nn
import numpy as np
from sklearn.preprocessing import MinMaxScaler
import logging

logger = logging.getLogger(__name__)

class LSTMPredictor(nn.Module):
    def __init__(self, input_size=5, hidden_size=64, num_layers=2, dropout=0.2):
        super().__init__()
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True, dropout=dropout)
        self.fc = nn.Sequential(
            nn.Linear(hidden_size, 32),
            nn.ReLU(),
            nn.Linear(32, 1),
        )

    def forward(self, x):
        h0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size)
        c0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size)
        out, _ = self.lstm(x, (h0, c0))
        out = self.fc(out[:, -1, :])
        return out


class CryptoLSTM:
    def __init__(self, lookback=30, epochs=50, lr=0.001):
        self.lookback = lookback
        self.epochs = epochs
        self.lr = lr
        self.model = LSTMPredictor()
        self.scaler = MinMaxScaler()
        self.price_scaler = MinMaxScaler()
        self.trained = False

    def prepare_data(self, df):
        """Prepare OHLCV data for LSTM training."""
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
        """Train the LSTM model on historical OHLCV data."""
        if df is None or len(df) < self.lookback + 20:
            logger.warning("Not enough data for LSTM training")
            return False

        try:
            X, y = self.prepare_data(df)
            if len(X) < 10:
                return False

            X_tensor = torch.FloatTensor(X)
            y_tensor = torch.FloatTensor(y).unsqueeze(1)

            # Train/val split
            split = int(len(X) * 0.8)
            X_train, y_train = X_tensor[:split], y_tensor[:split]

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
            logger.info(f"LSTM trained. Final loss: {loss.item():.6f}")
            return True

        except Exception as e:
            logger.error(f"LSTM training error: {e}")
            return False

    def predict(self, df):
        """Predict next price direction. Returns signal and confidence."""
        if not self.trained or df is None or len(df) < self.lookback:
            return {"signal": "HOLD", "confidence": 0, "predicted_direction": "NEUTRAL"}

        try:
            self.model.eval()
            features = df[['open', 'high', 'low', 'close', 'volume']].values
            scaled = self.scaler.transform(features)
            last_seq = scaled[-self.lookback:]

            X = torch.FloatTensor(last_seq).unsqueeze(0)
            with torch.no_grad():
                pred_scaled = self.model(X).item()

            # Inverse transform to get predicted price
            pred_price = self.price_scaler.inverse_transform([[pred_scaled]])[0][0]
            current_price = df['close'].iloc[-1]
            pct_change = (pred_price - current_price) / current_price * 100

            # Determine signal based on predicted direction
            if pct_change > 0.15:
                signal = "BUY"
                direction = "UP"
            elif pct_change < -0.15:
                signal = "SELL"
                direction = "DOWN"
            else:
                signal = "HOLD"
                direction = "NEUTRAL"

            confidence = min(abs(pct_change) * 20, 100)

            return {
                "signal": signal,
                "confidence": round(confidence, 1),
                "predicted_direction": direction,
                "predicted_change_pct": round(pct_change, 4),
                "predicted_price": round(pred_price, 2),
                "current_price": round(current_price, 2),
            }

        except Exception as e:
            logger.error(f"LSTM prediction error: {e}")
            return {"signal": "HOLD", "confidence": 0, "predicted_direction": "NEUTRAL"}


# Singleton instance
lstm_models = {}

def get_lstm(symbol="BTC/USDT"):
    if symbol not in lstm_models:
        lstm_models[symbol] = CryptoLSTM(lookback=30, epochs=30)
    return lstm_models[symbol]
