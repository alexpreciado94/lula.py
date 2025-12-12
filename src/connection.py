import ccxt
import time
import os
import sys

class KrakenConnection:
    def __init__(self):
        # Leemos las claves inyectadas por Docker desde el .env
        api_key = os.getenv('API_KEY')
        secret_key = os.getenv('SECRET_KEY')
        
        if not api_key or not secret_key:
            print("❌ ERROR FATAL: No hay API Keys en el archivo .env")
            sys.exit(1)

        # Configuración específica para Kraken
        self.exchange = ccxt.kraken({
            'apiKey': api_key,
            'secret': secret_key,
            'enableRateLimit': True,
            'options': {
                'adjustForTimeDifference': True  # Sincroniza reloj para evitar errores
            }
        })
    
    def get_data(self, symbol, limit=100):
        """
        Descarga velas (OHLCV). Reintenta 3 veces si hay fallo de red.
        """
        for i in range(3):
            try:
                bars = self.exchange.fetch_ohlcv(symbol, timeframe='1h', limit=limit)
                if bars and len(bars) > 0:
                    return bars
            except Exception as e:
                print(f"⚠️ Aviso: Fallo de red obteniendo {symbol} ({i+1}/3).")
                time.sleep(5)
        
        print(f"❌ Error: Kraken no respondió para {symbol} tras 3 intentos.")
        return None

    def get_balance(self):
        """Devuelve el balance completo."""
        try:
            return self.exchange.fetch_balance()
        except Exception as e:
            print(f"❌ Error consultando saldo: {e}")
            return None

    def execute_order(self, symbol, type, side, amount):
        """
        Lanza una orden al mercado.
        side: 'buy' / 'sell'
        type: 'market' / 'limit'
        """
        try:
            order = self.exchange.create_order(symbol, type, side, amount)
            print(f"✅ ORDEN EJECUTADA: {side} {amount} de {symbol}")
            return order
        except Exception as e:
            print(f"❌ Error crítico ejecutando orden: {e}")
            return None