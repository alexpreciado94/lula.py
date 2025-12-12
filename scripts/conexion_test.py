import ccxt
import os
import sys
from dotenv import load_dotenv

# --- CONFIGURACIÓN VISUAL ---
VERDE = '\033[92m'
AMARILLO = '\033[93m'
ROJO = '\033[91m'
RESET = '\033[0m'

def probar_conexion():
    print(f"{AMARILLO}🔌 Iniciando Test de Conexión a Kraken...{RESET}")

    # 1. CARGAR ENTORNO (.env está un nivel arriba)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    env_path = os.path.join(project_root, '.env')

    print(f"📂 Buscando archivo .env en: {env_path}")

    if os.path.exists(env_path):
        load_dotenv(env_path)
        print(f"{VERDE}✅ Archivo .env encontrado.{RESET}")
    else:
        print(f"{ROJO}❌ Error: No se encuentra el archivo .env en la raíz.{RESET}")
        print("   Asegúrate de haber creado el archivo .env con tus claves.")
        return

    # 2. CONFIGURAR KRAKEN
    api_key = os.getenv('API_KEY')
    secret_key = os.getenv('SECRET_KEY')

    if not api_key or not secret_key:
        print(f"{ROJO}❌ Error: Las claves API_KEY o SECRET_KEY están vacías en el .env{RESET}")
        return

    try:
        exchange = ccxt.kraken({
            'apiKey': api_key,
            'secret': secret_key,
            'enableRateLimit': True,
        })
        
        # 3. PRUEBA PÚBLICA (Ver precio de Monero)
        print(f"\n{AMARILLO}📡 Paso 1: Probando API Pública (Consultar precio XMR)...{RESET}")
        ticker = exchange.fetch_ticker('XMR/USD')
        precio = ticker['last']
        print(f"{VERDE}✅ ¡Conexión Exitosa! Precio XMR: ${precio} USD{RESET}")

        # 4. PRUEBA PRIVADA (Ver saldo)
        print(f"\n{AMARILLO}🔐 Paso 2: Probando API Privada (Consultar Saldo)...{RESET}")
        balance = exchange.fetch_balance()
        
        # Filtrar solo lo que tiene saldo positivo para mostrar
        total_balance = balance['total']
        activos = {k: v for k, v in total_balance.items() if v > 0}

        print(f"{VERDE}✅ ¡Autenticación Exitosa!{RESET}")
        print(f"💰 Tu Cartera en Kraken:")
        if activos:
            for moneda, cantidad in activos.items():
                print(f"   - {moneda}: {cantidad}")
        else:
            print("   (La cuenta está vacía, pero la conexión funciona)")

    except ccxt.AuthenticationError:
        print(f"{ROJO}❌ Error de Autenticación: Tus API Keys son incorrectas o no tienen permisos.{RESET}")
    except ccxt.NetworkError:
        print(f"{ROJO}❌ Error de Red: No se puede conectar con Kraken. Revisa tu internet.{RESET}")
    except Exception as e:
        print(f"{ROJO}❌ Error desconocido: {e}{RESET}")

if __name__ == "__main__":
    try:
        probar_conexion()
    except KeyboardInterrupt:
        print("\nTest cancelado por el usuario.")