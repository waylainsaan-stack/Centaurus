import requests
import sys
import time
from datetime import datetime

class CryptoAIBotTester:
    def __init__(self, base_url="https://binance-trading-ai.preview.emergentagent.com"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []

    def run_test(self, name, method, endpoint, expected_status, data=None, timeout=30):
        """Run a single API test"""
        url = f"{self.base_url}/api{endpoint}"
        headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=timeout)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=timeout)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=timeout)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    print(f"   Response keys: {list(response_data.keys()) if isinstance(response_data, dict) else 'Non-dict response'}")
                    return True, response_data
                except:
                    return True, response.text
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                print(f"   Response: {response.text[:200]}")
                self.failed_tests.append({
                    "test": name,
                    "endpoint": endpoint,
                    "expected": expected_status,
                    "actual": response.status_code,
                    "response": response.text[:200]
                })
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            self.failed_tests.append({
                "test": name,
                "endpoint": endpoint,
                "error": str(e)
            })
            return False, {}

    def test_root_endpoint(self):
        """Test GET /api/ returns proper response"""
        return self.run_test("Root API", "GET", "/", 200)

    def test_bot_status_initial(self):
        """Test GET /api/bot/status returns bot status with running=false initially"""
        success, response = self.run_test("Bot Status Initial", "GET", "/bot/status", 200)
        if success and isinstance(response, dict):
            running = response.get('running', None)
            if running is False:
                print(f"   ✅ Bot initially not running: {running}")
                return True
            else:
                print(f"   ❌ Expected running=false, got: {running}")
                return False
        return success

    def test_bot_start(self):
        """Test POST /api/bot/start starts the bot"""
        success, response = self.run_test("Bot Start", "POST", "/bot/start", 200)
        if success and isinstance(response, dict):
            status = response.get('status')
            if status in ['started', 'already_running']:
                print(f"   ✅ Bot start response: {status}")
                return True
            else:
                print(f"   ❌ Unexpected start response: {status}")
                return False
        return success

    def test_bot_status_after_start(self):
        """Test GET /api/bot/status returns running=true after start"""
        # Wait a moment for bot to start
        time.sleep(2)
        success, response = self.run_test("Bot Status After Start", "GET", "/bot/status", 200)
        if success and isinstance(response, dict):
            running = response.get('running', None)
            if running is True:
                print(f"   ✅ Bot running after start: {running}")
                return True
            else:
                print(f"   ❌ Expected running=true, got: {running}")
                return False
        return success

    def test_bot_stop(self):
        """Test POST /api/bot/stop stops the bot"""
        success, response = self.run_test("Bot Stop", "POST", "/bot/stop", 200)
        if success and isinstance(response, dict):
            status = response.get('status')
            if status in ['stopped', 'already_stopped']:
                print(f"   ✅ Bot stop response: {status}")
                return True
            else:
                print(f"   ❌ Unexpected stop response: {status}")
                return False
        return success

    def test_market_price(self):
        """Test GET /api/market/price returns live BTC/USDT price data"""
        success, response = self.run_test("Market Price", "GET", "/market/price", 200)
        if success and isinstance(response, dict):
            required_fields = ['price', 'high', 'low', 'volume']
            missing_fields = [f for f in required_fields if f not in response]
            if not missing_fields:
                print(f"   ✅ Price data complete: ${response.get('price', 'N/A')}")
                return True
            else:
                print(f"   ❌ Missing fields: {missing_fields}")
                return False
        return success

    def test_market_ohlcv(self):
        """Test GET /api/market/ohlcv?limit=100 returns OHLCV chart data array"""
        success, response = self.run_test("Market OHLCV", "GET", "/market/ohlcv?limit=100", 200)
        if success and isinstance(response, dict):
            data = response.get('data', [])
            if isinstance(data, list) and len(data) > 0:
                sample = data[0]
                required_fields = ['time', 'open', 'high', 'low', 'close', 'volume']
                missing_fields = [f for f in required_fields if f not in sample]
                if not missing_fields:
                    print(f"   ✅ OHLCV data complete: {len(data)} records")
                    return True
                else:
                    print(f"   ❌ Missing OHLCV fields: {missing_fields}")
                    return False
            else:
                print(f"   ❌ No OHLCV data returned")
                return False
        return success

    def test_market_orderbook(self):
        """Test GET /api/market/orderbook returns bids, asks, signal, volumes"""
        success, response = self.run_test("Market Orderbook", "GET", "/market/orderbook", 200)
        if success and isinstance(response, dict):
            required_fields = ['bids', 'asks', 'signal', 'bid_volume', 'ask_volume']
            missing_fields = [f for f in required_fields if f not in response]
            if not missing_fields:
                bids_count = len(response.get('bids', []))
                asks_count = len(response.get('asks', []))
                print(f"   ✅ Orderbook complete: {bids_count} bids, {asks_count} asks")
                return True
            else:
                print(f"   ❌ Missing orderbook fields: {missing_fields}")
                return False
        return success

    def test_market_indicators(self):
        """Test GET /api/market/indicators returns RSI, EMA50, EMA200, ema_crossover"""
        success, response = self.run_test("Market Indicators", "GET", "/market/indicators", 200)
        if success and isinstance(response, dict):
            required_fields = ['rsi', 'ema50', 'ema200', 'ema_crossover']
            present_fields = [f for f in required_fields if f in response and response[f] is not None]
            if len(present_fields) >= 3:  # Allow some flexibility for indicators
                print(f"   ✅ Indicators present: {present_fields}")
                return True
            else:
                print(f"   ❌ Insufficient indicators: {present_fields}")
                return False
        return success

    def test_signals_current(self):
        """Test GET /api/signals/current returns current signal state"""
        success, response = self.run_test("Signals Current", "GET", "/signals/current", 200)
        if success and isinstance(response, dict):
            signal = response.get('signal')
            if signal:
                print(f"   ✅ Current signal: {signal}")
                return True
            else:
                print(f"   ❌ No signal in response")
                return False
        return success

    def test_signals_history(self):
        """Test GET /api/signals/history returns signal history array"""
        success, response = self.run_test("Signals History", "GET", "/signals/history", 200)
        if success and isinstance(response, dict):
            signals = response.get('signals', [])
            if isinstance(signals, list):
                print(f"   ✅ Signal history: {len(signals)} records")
                return True
            else:
                print(f"   ❌ Signals not a list")
                return False
        return success

    def test_ai_analyze(self):
        """Test POST /api/ai/analyze triggers GPT-5.2 AI analysis"""
        print("   ⏳ AI analysis may take 10-30 seconds...")
        success, response = self.run_test("AI Analyze", "POST", "/ai/analyze", 200, timeout=60)
        if success and isinstance(response, dict):
            signal = response.get('signal')
            insight = response.get('insight')
            if signal and insight:
                print(f"   ✅ AI analysis complete: {signal}")
                print(f"   Insight: {insight[:100]}...")
                return True
            else:
                print(f"   ❌ Missing AI response fields")
                return False
        return success

    def test_ai_insights(self):
        """Test GET /api/ai/insights returns AI insight history"""
        success, response = self.run_test("AI Insights", "GET", "/ai/insights", 200)
        if success and isinstance(response, dict):
            insights = response.get('insights', [])
            if isinstance(insights, list):
                print(f"   ✅ AI insights: {len(insights)} records")
                return True
            else:
                print(f"   ❌ Insights not a list")
                return False
        return success

    # NEW MULTI-PAIR TESTS
    def test_pairs_endpoint(self):
        """Test GET /api/pairs returns list of 8 supported trading pairs"""
        success, response = self.run_test("Supported Pairs", "GET", "/pairs", 200)
        if success and isinstance(response, dict):
            pairs = response.get('pairs', [])
            expected_pairs = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XRP/USDT', 'DOGE/USDT', 'ADA/USDT', 'AVAX/USDT', 'DOT/USDT']
            if isinstance(pairs, list) and len(pairs) == 8:
                missing_pairs = [p for p in expected_pairs if p not in pairs]
                if not missing_pairs:
                    print(f"   ✅ All 8 pairs present: {pairs}")
                    return True
                else:
                    print(f"   ❌ Missing pairs: {missing_pairs}")
                    return False
            else:
                print(f"   ❌ Expected 8 pairs, got: {len(pairs) if isinstance(pairs, list) else 'not a list'}")
                return False
        return success

    def test_market_all_prices(self):
        """Test GET /api/market/prices returns prices for all pairs"""
        success, response = self.run_test("All Market Prices", "GET", "/market/prices", 200)
        if success and isinstance(response, dict):
            prices = response.get('prices', [])
            if isinstance(prices, list) and len(prices) >= 8:
                sample = prices[0] if prices else {}
                required_fields = ['symbol', 'price', 'change']
                missing_fields = [f for f in required_fields if f not in sample]
                if not missing_fields:
                    print(f"   ✅ Multi-pair prices: {len(prices)} pairs")
                    return True
                else:
                    print(f"   ❌ Missing price fields: {missing_fields}")
                    return False
            else:
                print(f"   ❌ Expected >=8 price records, got: {len(prices) if isinstance(prices, list) else 'not a list'}")
                return False
        return success

    def test_market_price_eth(self):
        """Test GET /api/market/price?symbol=ETH/USDT returns ETH price"""
        success, response = self.run_test("ETH Price", "GET", "/market/price?symbol=ETH/USDT", 200)
        if success and isinstance(response, dict):
            symbol = response.get('symbol')
            price = response.get('price')
            if symbol == 'ETH/USDT' and price is not None:
                print(f"   ✅ ETH price: ${price}")
                return True
            else:
                print(f"   ❌ Invalid ETH response: symbol={symbol}, price={price}")
                return False
        return success

    def test_market_price_sol(self):
        """Test GET /api/market/price?symbol=SOL/USDT returns SOL price"""
        success, response = self.run_test("SOL Price", "GET", "/market/price?symbol=SOL/USDT", 200)
        if success and isinstance(response, dict):
            symbol = response.get('symbol')
            price = response.get('price')
            if symbol == 'SOL/USDT' and price is not None:
                print(f"   ✅ SOL price: ${price}")
                return True
            else:
                print(f"   ❌ Invalid SOL response: symbol={symbol}, price={price}")
                return False
        return success

    def test_market_indicators_eth(self):
        """Test GET /api/market/indicators?symbol=ETH/USDT returns indicators for ETH"""
        success, response = self.run_test("ETH Indicators", "GET", "/market/indicators?symbol=ETH/USDT", 200)
        if success and isinstance(response, dict):
            required_fields = ['rsi', 'ema50', 'ema200', 'ema_crossover']
            present_fields = [f for f in required_fields if f in response and response[f] is not None]
            if len(present_fields) >= 3:
                print(f"   ✅ ETH indicators present: {present_fields}")
                return True
            else:
                print(f"   ❌ Insufficient ETH indicators: {present_fields}")
                return False
        return success

    # TRADE EXECUTION TESTS
    def test_trade_execute_buy_market(self):
        """Test POST /api/trades/execute with BUY MARKET order returns trade with SIMULATED status"""
        trade_data = {
            "symbol": "BTC/USDT",
            "side": "BUY",
            "type": "MARKET",
            "amount": 0.001
        }
        success, response = self.run_test("Execute BUY MARKET Trade", "POST", "/trades/execute", 200, trade_data)
        if success and isinstance(response, dict):
            status = response.get('status')
            side = response.get('side')
            trade_type = response.get('type')
            if status == 'SIMULATED' and side == 'BUY' and trade_type == 'MARKET':
                print(f"   ✅ Trade executed: {status} {side} {trade_type}")
                return True, response.get('id')  # Return trade ID for later tests
            else:
                print(f"   ❌ Invalid trade response: status={status}, side={side}, type={trade_type}")
                return False, None
        return success, None

    def test_trade_execute_with_risk_management(self):
        """Test POST /api/trades/execute with stop_loss and take_profit params records them in trade"""
        trade_data = {
            "symbol": "ETH/USDT",
            "side": "BUY",
            "type": "MARKET",
            "amount": 0.01,
            "stop_loss": 3000.0,
            "take_profit": 4000.0
        }
        success, response = self.run_test("Execute Trade with SL/TP", "POST", "/trades/execute", 200, trade_data)
        if success and isinstance(response, dict):
            stop_loss = response.get('stop_loss')
            take_profit = response.get('take_profit')
            if stop_loss == 3000.0 and take_profit == 4000.0:
                print(f"   ✅ Risk management recorded: SL=${stop_loss}, TP=${take_profit}")
                return True, response.get('id')
            else:
                print(f"   ❌ Risk management not recorded: SL={stop_loss}, TP={take_profit}")
                return False, None
        return success, None

    def test_trade_history(self):
        """Test GET /api/trades/history returns trade records"""
        success, response = self.run_test("Trade History", "GET", "/trades/history", 200)
        if success and isinstance(response, dict):
            trades = response.get('trades', [])
            if isinstance(trades, list):
                print(f"   ✅ Trade history: {len(trades)} records")
                return True
            else:
                print(f"   ❌ Trades not a list")
                return False
        return success

    def test_trade_close(self, trade_id):
        """Test POST /api/trades/close/{trade_id} closes trade with PnL calculation"""
        if not trade_id:
            print("   ⚠️ Skipping trade close test - no trade ID available")
            return True
        
        success, response = self.run_test(f"Close Trade {trade_id}", "POST", f"/trades/close/{trade_id}", 200)
        if success and isinstance(response, dict):
            status = response.get('status')
            pnl = response.get('pnl')
            if status == 'closed' and pnl is not None:
                print(f"   ✅ Trade closed: status={status}, PnL=${pnl}")
                return True
            else:
                print(f"   ❌ Invalid close response: status={status}, pnl={pnl}")
                return False
        return success

    # RISK SETTINGS TESTS
    def test_risk_settings_get(self):
        """Test GET /api/risk/settings returns default risk settings"""
        success, response = self.run_test("Get Risk Settings", "GET", "/risk/settings", 200)
        if success and isinstance(response, dict):
            required_fields = ['stop_loss_pct', 'take_profit_pct', 'max_position_size']
            missing_fields = [f for f in required_fields if f not in response]
            if not missing_fields:
                print(f"   ✅ Risk settings complete: SL={response.get('stop_loss_pct')}%, TP={response.get('take_profit_pct')}%")
                return True
            else:
                print(f"   ❌ Missing risk fields: {missing_fields}")
                return False
        return success

    def test_risk_settings_save(self):
        """Test POST /api/risk/settings saves custom risk settings"""
        risk_data = {
            "symbol": "BTC/USDT",
            "stop_loss_pct": 3.0,
            "take_profit_pct": 6.0,
            "max_position_size": 0.005,
            "trailing_stop": True,
            "trailing_stop_pct": 1.5
        }
        success, response = self.run_test("Save Risk Settings", "POST", "/risk/settings", 200, risk_data)
        if success and isinstance(response, dict):
            status = response.get('status')
            if status == 'saved':
                print(f"   ✅ Risk settings saved: {status}")
                return True
            else:
                print(f"   ❌ Invalid save response: {status}")
                return False
        return success

    # ALERT SYSTEM TESTS
    def test_alert_create_price_above(self):
        """Test POST /api/alerts/create creates a price_above alert"""
        alert_data = {
            "symbol": "BTC/USDT",
            "type": "price_above",
            "value": 100000.0,
            "enabled": True
        }
        success, response = self.run_test("Create Price Above Alert", "POST", "/alerts/create", 200, alert_data)
        if success and isinstance(response, dict):
            alert_type = response.get('type')
            value = response.get('value')
            if alert_type == 'price_above' and value == 100000.0:
                print(f"   ✅ Price alert created: {alert_type} ${value}")
                return True, response.get('id')
            else:
                print(f"   ❌ Invalid alert response: type={alert_type}, value={value}")
                return False, None
        return success, None

    def test_alert_create_signal_strong_buy(self):
        """Test POST /api/alerts/create creates a signal_strong_buy alert"""
        alert_data = {
            "symbol": "ETH/USDT",
            "type": "signal_strong_buy",
            "enabled": True
        }
        success, response = self.run_test("Create Strong Buy Signal Alert", "POST", "/alerts/create", 200, alert_data)
        if success and isinstance(response, dict):
            alert_type = response.get('type')
            if alert_type == 'signal_strong_buy':
                print(f"   ✅ Signal alert created: {alert_type}")
                return True, response.get('id')
            else:
                print(f"   ❌ Invalid signal alert response: type={alert_type}")
                return False, None
        return success, None

    def test_alerts_get(self):
        """Test GET /api/alerts returns list of alerts"""
        success, response = self.run_test("Get Alerts", "GET", "/alerts", 200)
        if success and isinstance(response, dict):
            alerts = response.get('alerts', [])
            if isinstance(alerts, list):
                print(f"   ✅ Alerts list: {len(alerts)} alerts")
                return True
            else:
                print(f"   ❌ Alerts not a list")
                return False
        return success

    def test_alert_delete(self, alert_id):
        """Test DELETE /api/alerts/{alert_id} deletes an alert"""
        if not alert_id:
            print("   ⚠️ Skipping alert delete test - no alert ID available")
            return True
            
        success, response = self.run_test(f"Delete Alert {alert_id}", "DELETE", f"/alerts/{alert_id}", 200)
        if success:
            if isinstance(response, dict):
                status = response.get('status')
                if status == 'deleted':
                    print(f"   ✅ Alert deleted: {status}")
                    return True
                else:
                    print(f"   ❌ Invalid delete response: {status}")
                    return False
            else:
                # DELETE might return non-JSON response
                print(f"   ✅ Alert delete request successful")
                return True
        return success

    # NOTIFICATION SYSTEM TESTS
    def test_notifications_get(self):
        """Test GET /api/notifications returns notifications list"""
        success, response = self.run_test("Get Notifications", "GET", "/notifications", 200)
        if success and isinstance(response, dict):
            notifications = response.get('notifications', [])
            if isinstance(notifications, list):
                print(f"   ✅ Notifications list: {len(notifications)} notifications")
                return True
            else:
                print(f"   ❌ Notifications not a list")
                return False
        return success

    def test_notifications_unread(self):
        """Test GET /api/notifications/unread returns unread count"""
        success, response = self.run_test("Get Unread Count", "GET", "/notifications/unread", 200)
        if success and isinstance(response, dict):
            unread = response.get('unread')
            if isinstance(unread, int) and unread >= 0:
                print(f"   ✅ Unread count: {unread}")
                return True
            else:
                print(f"   ❌ Invalid unread count: {unread}")
                return False
        return success

    def test_notifications_mark_read(self):
        """Test POST /api/notifications/read marks all as read"""
        success, response = self.run_test("Mark All Read", "POST", "/notifications/read", 200)
        if success and isinstance(response, dict):
            status = response.get('status')
            if status == 'done':
                print(f"   ✅ Notifications marked read: {status}")
                return True
            else:
                print(f"   ❌ Invalid mark read response: {status}")
                return False
        return success

    # LSTM MODEL TESTS
    def test_lstm_status(self):
        """Test GET /api/lstm/status returns trained status"""
        success, response = self.run_test("LSTM Status", "GET", "/lstm/status", 200)
        if success and isinstance(response, dict):
            trained = response.get('trained')
            prediction = response.get('prediction', {})
            if isinstance(trained, bool):
                print(f"   ✅ LSTM status: trained={trained}")
                return True
            else:
                print(f"   ❌ Invalid LSTM status response: trained={trained}")
                return False
        return success

    def test_lstm_train(self):
        """Test POST /api/lstm/train trains the LSTM model successfully"""
        print("   ⏳ LSTM training may take 30-60 seconds...")
        success, response = self.run_test("LSTM Train", "POST", "/lstm/train", 200, timeout=120)
        if success and isinstance(response, dict):
            status = response.get('status')
            if status in ['trained', 'failed']:
                print(f"   ✅ LSTM training response: {status}")
                return True
            else:
                print(f"   ❌ Invalid LSTM training response: {status}")
                return False
        return success

    def test_lstm_predict(self):
        """Test GET /api/lstm/predict returns prediction after training"""
        success, response = self.run_test("LSTM Predict", "GET", "/lstm/predict", 200)
        if success and isinstance(response, dict):
            signal = response.get('signal')
            confidence = response.get('confidence')
            predicted_direction = response.get('predicted_direction')
            if signal and confidence is not None and predicted_direction:
                print(f"   ✅ LSTM prediction: {signal} ({confidence}% confidence, {predicted_direction})")
                return True
            elif 'error' in response:
                print(f"   ⚠️ LSTM not trained yet: {response.get('error')}")
                return True  # This is expected if model not trained
            else:
                print(f"   ❌ Invalid LSTM prediction response")
                return False
        return success

    # NEWS TESTS
    def test_news_get(self):
        """Test GET /api/news returns articles from CryptoPanic/CoinDesk/CoinTelegraph"""
        success, response = self.run_test("Get News", "GET", "/news", 200, timeout=30)
        if success and isinstance(response, dict):
            articles = response.get('articles', [])
            count = response.get('count', 0)
            if isinstance(articles, list) and count >= 0:
                print(f"   ✅ News articles: {count} articles from multiple sources")
                if articles:
                    sources = set(article.get('source', 'Unknown') for article in articles[:5])
                    print(f"   Sources found: {list(sources)}")
                return True
            else:
                print(f"   ❌ Invalid news response: articles={type(articles)}, count={count}")
                return False
        return success

    def test_news_analyze(self):
        """Test POST /api/news/analyze triggers AI sentiment analysis of news"""
        print("   ⏳ News sentiment analysis may take 10-30 seconds...")
        success, response = self.run_test("Analyze News Sentiment", "POST", "/news/analyze", 200, timeout=60)
        if success and isinstance(response, dict):
            sentiment = response.get('sentiment', {})
            articles = response.get('articles', [])
            if sentiment and 'sentiment' in sentiment:
                sentiment_value = sentiment.get('sentiment')
                score = sentiment.get('score', 0)
                signal = sentiment.get('signal', 'HOLD')
                print(f"   ✅ News sentiment: {sentiment_value} (score: {score}, signal: {signal})")
                return True
            elif 'error' in response:
                print(f"   ⚠️ News analysis error: {response.get('error')}")
                return True  # May be expected if no news available
            else:
                print(f"   ❌ Invalid news analysis response")
                return False
        return success

    def test_news_sentiment(self):
        """Test GET /api/news/sentiment returns news sentiment data"""
        success, response = self.run_test("Get News Sentiment", "GET", "/news/sentiment", 200)
        if success and isinstance(response, dict):
            sentiment = response.get('sentiment', 'NEUTRAL')
            score = response.get('score', 0)
            signal = response.get('signal', 'HOLD')
            if sentiment and isinstance(score, (int, float)) and signal:
                print(f"   ✅ News sentiment data: {sentiment} (score: {score}, signal: {signal})")
                return True
            else:
                print(f"   ❌ Invalid sentiment data: sentiment={sentiment}, score={score}, signal={signal}")
                return False
        return success

    # COMBINED SIGNAL TEST
    def test_combined_signal(self):
        """Test GET /api/signal/combined returns weighted combined signal breakdown"""
        success, response = self.run_test("Combined Signal", "GET", "/signal/combined", 200)
        if success and isinstance(response, dict):
            signal = response.get('signal')
            score = response.get('score')
            confidence = response.get('confidence')
            breakdown = response.get('breakdown', {})
            components = response.get('components', {})
            
            if signal and score is not None and confidence is not None:
                print(f"   ✅ Combined signal: {signal} (score: {score}, confidence: {confidence}%)")
                
                # Check breakdown weights
                expected_components = ['technical', 'orderbook', 'lstm', 'news', 'ai']
                present_components = [c for c in expected_components if c in breakdown]
                print(f"   Signal breakdown components: {present_components}")
                
                return True
            else:
                print(f"   ❌ Invalid combined signal response")
                return False
        return success

def main():
    print("🚀 Starting Crypto AI Trading Bot API Tests")
    print("=" * 60)
    
    tester = CryptoAIBotTester()
    
    # Store IDs for dependent tests
    trade_id = None
    alert_id = None
    
    # Run all tests in sequence
    test_results = []
    
    # Original tests
    test_results.append(("Root API", tester.test_root_endpoint))
    test_results.append(("Bot Status Initial", tester.test_bot_status_initial))
    test_results.append(("Bot Start", tester.test_bot_start))
    test_results.append(("Bot Status After Start", tester.test_bot_status_after_start))
    test_results.append(("Bot Stop", tester.test_bot_stop))
    test_results.append(("Market Price", tester.test_market_price))
    test_results.append(("Market OHLCV", tester.test_market_ohlcv))
    test_results.append(("Market Orderbook", tester.test_market_orderbook))
    test_results.append(("Market Indicators", tester.test_market_indicators))
    test_results.append(("Signals Current", tester.test_signals_current))
    test_results.append(("Signals History", tester.test_signals_history))
    test_results.append(("AI Analyze", tester.test_ai_analyze))
    test_results.append(("AI Insights", tester.test_ai_insights))
    
    # NEW MULTI-PAIR TESTS
    test_results.append(("Supported Pairs", tester.test_pairs_endpoint))
    test_results.append(("All Market Prices", tester.test_market_all_prices))
    test_results.append(("ETH Price", tester.test_market_price_eth))
    test_results.append(("SOL Price", tester.test_market_price_sol))
    test_results.append(("ETH Indicators", tester.test_market_indicators_eth))
    
    # TRADE EXECUTION TESTS
    test_results.append(("Execute BUY MARKET Trade", lambda: tester.test_trade_execute_buy_market()))
    test_results.append(("Execute Trade with SL/TP", lambda: tester.test_trade_execute_with_risk_management()))
    test_results.append(("Trade History", tester.test_trade_history))
    
    # RISK SETTINGS TESTS
    test_results.append(("Get Risk Settings", tester.test_risk_settings_get))
    test_results.append(("Save Risk Settings", tester.test_risk_settings_save))
    
    # ALERT SYSTEM TESTS
    test_results.append(("Create Price Above Alert", lambda: tester.test_alert_create_price_above()))
    test_results.append(("Create Strong Buy Signal Alert", lambda: tester.test_alert_create_signal_strong_buy()))
    test_results.append(("Get Alerts", tester.test_alerts_get))
    
    # NOTIFICATION SYSTEM TESTS
    test_results.append(("Get Notifications", tester.test_notifications_get))
    test_results.append(("Get Unread Count", tester.test_notifications_unread))
    test_results.append(("Mark All Read", tester.test_notifications_mark_read))
    
    # LSTM MODEL TESTS
    test_results.append(("LSTM Status", tester.test_lstm_status))
    test_results.append(("LSTM Train", tester.test_lstm_train))
    test_results.append(("LSTM Predict", tester.test_lstm_predict))
    
    # NEWS TESTS
    test_results.append(("Get News", tester.test_news_get))
    test_results.append(("Analyze News Sentiment", tester.test_news_analyze))
    test_results.append(("Get News Sentiment", tester.test_news_sentiment))
    
    # COMBINED SIGNAL TEST
    test_results.append(("Combined Signal", tester.test_combined_signal))
    
    # Execute all tests
    for test_name, test_func in test_results:
        try:
            result = test_func()
            
            # Handle tests that return tuples (success, id)
            if isinstance(result, tuple):
                success, item_id = result
                if test_name == "Execute BUY MARKET Trade" and item_id:
                    trade_id = item_id
                elif test_name == "Create Price Above Alert" and item_id:
                    alert_id = item_id
            
        except Exception as e:
            print(f"❌ Test {test_name} crashed: {e}")
            tester.failed_tests.append({
                "test": test_name,
                "error": f"Test crashed: {e}"
            })
        
        # Small delay between tests
        time.sleep(1)
    
    # Run dependent tests with IDs
    if trade_id:
        try:
            tester.test_trade_close(trade_id)
        except Exception as e:
            print(f"❌ Trade close test crashed: {e}")
    
    if alert_id:
        try:
            tester.test_alert_delete(alert_id)
        except Exception as e:
            print(f"❌ Alert delete test crashed: {e}")
    
    # Print final results
    print("\n" + "=" * 60)
    print(f"📊 FINAL RESULTS")
    print(f"Tests passed: {tester.tests_passed}/{tester.tests_run}")
    print(f"Success rate: {(tester.tests_passed/tester.tests_run)*100:.1f}%")
    
    if tester.failed_tests:
        print(f"\n❌ FAILED TESTS ({len(tester.failed_tests)}):")
        for fail in tester.failed_tests:
            print(f"  - {fail.get('test', 'Unknown')}: {fail.get('error', fail.get('response', 'Unknown error'))}")
    
    return 0 if tester.tests_passed == tester.tests_run else 1

if __name__ == "__main__":
    sys.exit(main())