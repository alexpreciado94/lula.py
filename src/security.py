import os
from cryptography.fernet import Fernet
import ccxt

def get_exchange_secure(exchange_id):
    """Crea una conexión al exchange pasando por TOR"""
    config = {
        'apiKey': os.getenv('API_KEY'),
        'secret': os.getenv('SECRET_KEY'),
        'enableRateLimit': True,
        # ENRUTAMIENTO POR TOR (El contenedor se llama 'tor-proxy')
        'proxies': {
            'http': 'http://tor-proxy:8118',
            'https': 'http://tor-proxy:8118',
        }
    }
    
    # Instanciar dinámicamente (ej. ccxt.binance, ccxt.kraken)
    exchange_class = getattr(ccxt, exchange_id)
    return exchange_class(config)

def log_enc(message):
    """Escribe logs encriptados en el disco"""
    key = os.getenv('LOG_KEY').encode() # Clave de 32 bytes en base64
    f = Fernet(key)
    encrypted = f.encrypt(message.encode())
    
    with open('/app/logs/operations.enc', 'ab') as file:
        file.write(encrypted + b'\n')
    
    # Imprimir en consola (Docker logs) sin encriptar para debug rápido
    print(f"🔒 [SECURE LOG]: {message}")