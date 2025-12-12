import ccxt
import yfinance as yf
import time
import os
import sys

class KrakenConnection:
    def __init__(self):
        # 1. Cargar Credenciales desde variables de entorno (Docker/.env)
        api_key = os.getenv('API_KEY')
        secret_key = os.getenv('SECRET_KEY')
        
        if not api_key or not secret_key:
            print("❌ ERROR FATAL: No hay API Keys en el archivo .env")
            sys.exit(1)

        # 2. Inicializar Kraken con Rate Limiting activado
        self.exchange = ccxt.kraken({
            'apiKey': api_key,
            'secret': secret_key,
            'enableRateLimit': True,
            'options': {
                'adjustForTimeDifference': True  # Vital para evitar errores de sincronización
            }
        })
    
    def get_data(self, symbol, limit=100):
        """
        Descarga velas de Cripto (OHLCV) desde Kraken.
        Reintenta 3 veces si falla la red.
        """
        for i in range(3):
            try:
                # Descarga OHLCV (Open, High, Low, Close, Volume)
                bars = self.exchange.fetch_ohlcv(symbol, timeframe='1h', limit=limit)
                if bars and len(bars) > 0:
                    return bars
            except Exception as e:
                print(f"⚠️ Aviso: Fallo de red obteniendo {symbol} ({i+1}/3).")
                time.sleep(5)
        
        print(f"❌ Error: Kraken no respondió para {symbol} tras 3 intentos.")
        return None

    def get_sp500_data(self):
        """
        Descarga datos del S&P 500 (^GSPC) de Yahoo Finance.
        Necesario para el input Macro de la IA (Madness).
        """
        try:
            # Bajamos 7 días para asegurar cobertura de fines de semana
            # Intervalo 1h para coincidir con las velas de cripto
            spx = yf.download(tickers="^GSPC", period="7d", interval="1h", progress=False)
            
            if spx.empty:
                print("⚠️ Aviso: Yahoo Finance devolvió datos vacíos para SP500.")
                return None

            # Yahoo a veces devuelve estructuras complejas. 
            # Nos aseguramos de obtener solo la columna de cierre 'Close'.
            if 'Close' in spx.columns:
                return spx['Close']
            else:
                # Si la estructura cambia, cogemos la primera columna por defecto
                return spx.iloc[:, 0]
            
        except Exception as e:
            print(f"⚠️ Error obteniendo S&P 500: {e}")
            return None

    def get_balance(self):
        """Devuelve el balance completo de la cuenta."""
        try:
            return self.e