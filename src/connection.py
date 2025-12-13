import ccxt
import yfinance as yf
import time
import os
import sys

class DualExchangeManager:
    def __init__(self):
        print("🔌 Inicializando Sistema de Doble Exchange...")
        
        # 1. Configurar GENERADOR (Donde ganamos dinero)
        self.gen = self._connect(
            os.getenv('GEN_EXCHANGE_ID', 'binance'),
            os.getenv('GEN_API_KEY'),
            os.getenv('GEN_SECRET_KEY')
        )
        
        # 2. Configurar REFUGIO (Donde compramos Monero)
        self.safe = self._connect(
            os.getenv('XMR_EXCHANGE_ID', 'kucoin'),
            os.getenv('XMR_API_KEY'),
            os.getenv('XMR_SECRET_KEY'),
            os.getenv('XMR_PASSWORD')
        )
        
    def _connect(self, exchange_id, key, secret, password=None):
        if not key or not secret:
            print(f"❌ Falta API Key para {exchange_id}")
            sys.exit(1)
            
        if not hasattr(ccxt, exchange_id):
            print(f"❌ Exchange '{exchange_id}' no soportado por CCXT.")
            sys.exit(1)

        exchange_class = getattr(ccxt, exchange_id)
        config = {
            'apiKey': key, 
            'secret': secret, 
            'enableRateLimit': True,
            'options': {'defaultType': 'spot', 'adjustForTimeDifference': True}
        }
        if password: config['password'] = password
        
        return exchange_class(config)

    # --- MÉTODOS UNIVERSALES ---
    
    def validate_symbol(self, exchange_obj, symbol):
        try:
            if not exchange_obj.markets: exchange_obj.load_markets()
            return symbol in exchange_obj.markets
        except: return False

    def get_data(self, exchange_obj, symbol, limit=100):
        """Descarga velas OHLCV con reintentos"""
        for i in range(3):
            try:
                bars = exchange_obj.fetch_ohlcv(symbol, '1h', limit=limit)
                if bars: return bars
            except Exception as e:
                time.sleep(2)
        return None

    def get_balance(self, exchange_obj):
        try: return exchange_obj.fetch_balance()
        except: return None

    def execute_order(self, exchange_obj, symbol, side, amount):
        try:
            # Normalizar cantidad a la precisión del mercado
            amount = exchange_obj.amount_to_precision(symbol, amount)
            return exchange_obj.create_market_order(symbol, side, amount)
        except Exception as e:
            print(f"❌ Error Orden ({symbol}): {e}")
            return None

    def get_order_book_depth(self, exchange_obj, symbol):
        """Analiza liquidez para detectar Squeezes"""
        try:
            book = exchange_obj.fetch_order_book(symbol, limit=20)
            asks = book['asks']
            bids = book['bids']
            if not asks or not bids: return 0, 0
            
            liq_ask = sum([vol for price, vol in asks])
            liq_bid = sum([vol for price, vol in bids])
            return liq_ask, liq_bid
        except: return 0, 0

    def bridge_transfer(self, amount, target_address, network='TRX'):
        """Mueve USDT del Generador al Refugio"""
        try:
            # Check de saldo
            bal = self.get_balance(self.gen)
            free = bal.get('USDT', {}).get('free', 0)
            if amount > (free - 1.5): amount = free - 1.5
            
            if amount < 10: return None

            print(f"   🌉 PUENTE: Enviando {amount:.2f} USDT -> Refugio")
            return self.gen.withdraw('USDT', amount, target_address, params={'network': network})
        except Exception as e:
            print(f"   ❌ Error Puente: {e}")
            return None

    def withdraw_to_trezor(self, currency, amount, address):
        try:
            if amount <= 0: return None
            print(f"   ❄️ BÓVEDA: Retirando {amount} {currency} a Trezor...")
            return self.safe.withdraw(currency, amount, address)
        except Exception as e:
            print(f"   ❌ Error Bóveda: {e}")
            return None

    def get_sp500_data(self):
        try:
            spx = yf.download("^GSPC", period="7d", interval="1h", progress=False)
            if spx.empty: return None
            return spx['Close'] if 'Close' in spx.columns else spx.iloc[:, 0]
        except: return None