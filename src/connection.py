import ccxt
import yfinance as yf
import time
import os
import sys

class DualExchangeManager:
    def __init__(self):
        print("🔌 Inicializando Sistema de Doble Exchange...")
        
        # 1. Configurar GENERADOR (Binance, Bybit...)
        self.gen = self._connect(
            os.getenv('GEN_EXCHANGE_ID'),
            os.getenv('GEN_API_KEY'),
            os.getenv('GEN_SECRET_KEY')
        )
        
        # 2. Configurar REFUGIO (KuCoin, CoinEx...)
        self.safe = self._connect(
            os.getenv('XMR_EXCHANGE_ID'),
            os.getenv('XMR_API_KEY'),
            os.getenv('XMR_SECRET_KEY'),
            os.getenv('XMR_PASSWORD')
        )
        
    def _connect(self, exchange_id, key, secret, password=None):
        if not key or not secret:
            print(f"❌ Falta API Key para {exchange_id}")
            sys.exit(1)
            
        exchange_class = getattr(ccxt, exchange_id)
        config = {
            'apiKey': key, 
            'secret': secret, 
            'enableRateLimit': True,
            'options': {'defaultType': 'spot'}
        }
        if password: config['password'] = password
        
        return exchange_class(config)

    # --- MÉTODOS UNIVERSALES (Le pasas qué exchange usar) ---
    
    def get_data(self, exchange_obj, symbol, limit=100):
        for i in range(3):
            try:
                bars = exchange_obj.fetch_ohlcv(symbol, '1h', limit=limit)
                if bars: return bars
            except: time.sleep(2)
        return None

    def get_balance(self, exchange_obj):
        try: return exchange_obj.fetch_balance()
        except: return None

    def execute_order(self, exchange_obj, symbol, side, amount):
        try:
            # create_market_order es más directo
            return exchange_obj.create_market_order(symbol, side, amount)
        except Exception as e:
            print(f"❌ Error Orden: {e}")
            return None

    def withdraw_to_trezor(self, currency, amount, address):
        """
        💸 Mover fondos del Exchange B a tu Trezor Safe 3.
        REQUIERE PERMISOS DE 'WITHDRAWAL' EN LA API KEY.
        """
        try:
            # KuCoin y otros a veces requieren parámetros extra como 'chain'
            params = {} 
            
            # Verificar si hay saldo suficiente (restando fee de red aprox 0.0001 XMR)
            if amount <= 0: return None
            
            print(f"❄️ INICIANDO RETIRO A TREZOR: {amount} {currency}")
            
            tx = self.safe.withdraw(
                code=currency,
                amount=amount,
                address=address,
                params=params
            )
            print(f"✅ FONDOS ENVIADOS A BÓVEDA. TX ID: {tx['id']}")
            return tx
        except Exception as e:
            print(f"❌ Error en Retiro (Check API Permissions): {e}")
            return None

    def get_sp500_data(self):
        try:
            spx = yf.download("^GSPC", period="7d", interval="1h", progress=False)
            return spx['Close'] if not spx.empty else None
        except: return None