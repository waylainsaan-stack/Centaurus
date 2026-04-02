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

def main():
    print("🚀 Starting Crypto AI Trading Bot API Tests")
    print("=" * 60)
    
    tester = CryptoAIBotTester()
    
    # Run all tests in sequence
    test_methods = [
        tester.test_root_endpoint,
        tester.test_bot_status_initial,
        tester.test_bot_start,
        tester.test_bot_status_after_start,
        tester.test_bot_stop,
        tester.test_market_price,
        tester.test_market_ohlcv,
        tester.test_market_orderbook,
        tester.test_market_indicators,
        tester.test_signals_current,
        tester.test_signals_history,
        tester.test_ai_analyze,
        tester.test_ai_insights,
    ]
    
    for test_method in test_methods:
        try:
            test_method()
        except Exception as e:
            print(f"❌ Test {test_method.__name__} crashed: {e}")
            tester.failed_tests.append({
                "test": test_method.__name__,
                "error": f"Test crashed: {e}"
            })
        
        # Small delay between tests
        time.sleep(1)
    
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