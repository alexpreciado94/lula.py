import ccxt
import os
from dotenv import load_dotenv

# Cargar claves
load_dotenv()

def probar_conexion():
    try:
        # Iniciamos Binance (puedes cambiarlo a otro)
        exchange = ccxt.binance({
            'apiKey': os.getenv('API_KEY'),
            'secret': os.getenv('SECRET_KEY')
        })

        # Si no tienes claves aún, ccxt permite leer datos públicos sin ellas.
        # Pero para ver tu saldo, las necesitas.
        
        print("📡 Conectando con Binance...")
        
        # 1. Verificar precio de Bitcoin
        ticker = exchange.fetch_ticker('BTC/USDT')
        print(f"✅ Conexión Exitosa. Precio BTC: ${ticker['last']}")

        # 2. Verificar saldo (Solo si pusiste las API Keys reales)
        # balance = exchange.fetch_balance()
        # print(f"💰 Saldo USDT: {balance['USDT']['free']}")
        
    except Exception as e:
        print(f"❌ Error de conexión: {e}")

if __name__ == "__main__":
    probar_conexion()